"""Instalador y gestor gráfico; Tk se incluye en los binarios distribuidos."""
import argparse
import json
import os
from pathlib import Path
import platform
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from urllib.request import Request, urlopen
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
from instalacion_app import (CARPETA, actualizar_paquete, comando_arranque, instalacion_valida,
                             crear_accesos, ruta_predeterminada)


def metadata():
    recurso = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'instalador-build.json'
    if recurso.is_file():
        return json.loads(recurso.read_text(encoding='utf-8'))
    raise RuntimeError('Faltan los datos de esta versión. Construye primero el instalador con crear_instalador.py.')


def validar_destino(texto):
    if not texto.strip():
        raise ValueError('Elige una carpeta de instalación.')
    destino = Path(texto).expanduser()
    if not destino.is_absolute():
        raise ValueError('Elige una ruta completa con el botón Cambiar carpeta.')
    if destino == Path(destino.anchor) or destino == Path.home():
        raise ValueError('Elige una carpeta propia para Taller UFV, dentro de tu carpeta de usuario.')
    if destino.exists() and not destino.is_dir():
        raise ValueError('La ruta seleccionada es un archivo. Elige una carpeta.')
    return destino.resolve()


def preferencias(destino):
    archivo = Path(destino) / CARPETA / '.local/componentes.json'
    defecto = dict(escritorio=True, obsidian=True, opencode=True, calibrar=True)
    if archivo.is_file():
        valores = json.loads(archivo.read_text(encoding='utf-8'))
        if (not isinstance(valores, dict) or set(valores) != set(defecto)
                or any(type(valores.get(k)) is not bool for k in defecto)
                or (valores['escritorio'] and not valores['opencode'])):
            raise ValueError('La selección de componentes guardada no es válida. Revisa .local/componentes.json.')
        defecto.update({k: valores[k] for k in defecto})
    return defecto


def preparar_ambiente():
    if sys.platform == 'win32' and getattr(sys, 'frozen', False):
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    return dict(os.environ, _PYI_RESET_ENVIRONMENT='1', PYTHONUNBUFFERED='1', PYTHONUTF8='1',
                PYTHONIOENCODING='utf-8')


def abrir_terminal(proyecto, componentes):
    comando = comando_arranque(proyecto, 'iniciar', componentes)
    ambiente = preparar_ambiente()
    if sys.platform == 'win32':
        return subprocess.Popen(comando, cwd=proyecto, env=ambiente,
                                creationflags=subprocess.CREATE_NEW_CONSOLE)
    linea = shlex.join(comando)
    if sys.platform == 'darwin':
        # JSON genera un literal AppleScript seguro para comillas y barras.
        return subprocess.Popen(['osascript', '-e', 'tell application "Terminal" to do script ' + json.dumps(linea)], env=ambiente)
    for ejecutable, opciones in [('x-terminal-emulator', ['-e']), ('gnome-terminal', ['--']),
                                ('konsole', ['-e']), ('xterm', ['-e'])]:
        if shutil.which(ejecutable):
            return subprocess.Popen([ejecutable, *opciones, *comando], cwd=proyecto, env=ambiente)
    raise RuntimeError('No se encontró una terminal gráfica. Activa OpenCode Desktop o ejecuta iniciar.sh desde tu terminal.')


class Instalador:
    def __init__(self, ventana, meta, destino=None):
        self.ventana, self.meta = ventana, meta
        self.eventos = queue.Queue()
        self.ocupado = False
        self.proceso = None
        self.log_archivo = None
        self.destino = tk.StringVar(value=str(destino or ruta_predeterminada()))
        self.estado = tk.StringVar(value='Elige lo que quieres instalar en este equipo.')
        self.resumen = tk.StringVar()
        self.opciones = {k: tk.BooleanVar(value=v) for k, v in preferencias(self.destino.get()).items()}
        self.controles = []
        ventana.title('Taller UFV · Tu agente de la uni')
        altura = min(740, ventana.winfo_screenheight() - 110)
        ventana.geometry(f'800x{altura}')
        ventana.minsize(700, min(650, altura))
        ventana.protocol('WM_DELETE_WINDOW', self.cerrar)
        estilo = ttk.Style(ventana)
        if sys.platform == 'win32':
            estilo.theme_use('vista')
        estilo.configure('Titulo.TLabel', font=('TkDefaultFont', 23, 'bold'))
        estilo.configure('Seccion.TLabel', font=('TkDefaultFont', 11, 'bold'))
        estilo.configure('TButton', padding=(12, 7))
        estilo.configure('TCheckbutton', padding=(0, 3))
        principal = ttk.Frame(ventana, padding=26)
        principal.pack(fill='both', expand=True)
        principal.columnconfigure(0, weight=1)
        principal.rowconfigure(2, weight=1)
        principal.rowconfigure(9, minsize=80)
        ttk.Label(principal, text='Tu agente de la uni', style='Titulo.TLabel').grid(row=0, sticky='w')
        ttk.Label(principal, text='Apuntes, asignaturas, tareas y exámenes en tu ordenador.').grid(row=1, sticky='w', pady=(7, 22))

        zona = ttk.Frame(principal)
        zona.grid(row=2, sticky='nsew')
        zona.columnconfigure(0, weight=1)
        zona.rowconfigure(0, weight=1)
        self.lienzo = tk.Canvas(zona, height=365, highlightthickness=0, borderwidth=0)
        self.lienzo.grid(row=0, column=0, sticky='nsew')
        scroll_opciones = ttk.Scrollbar(zona, orient='vertical', command=self.lienzo.yview)
        scroll_opciones.grid(row=0, column=1, sticky='ns')
        self.lienzo.configure(yscrollcommand=scroll_opciones.set)
        configuracion = ttk.Frame(self.lienzo)
        configuracion.columnconfigure(0, weight=1)
        panel = self.lienzo.create_window(0, 0, window=configuracion, anchor='nw')
        configuracion.bind('<Configure>', lambda _: self.lienzo.configure(scrollregion=self.lienzo.bbox('all')))
        self.lienzo.bind('<Configure>', lambda e: self.lienzo.itemconfigure(panel, width=e.width))
        componentes = ttk.LabelFrame(configuracion, text='Qué quieres preparar', padding=(16, 10))
        componentes.grid(row=0, sticky='ew')
        componentes.columnconfigure(0, weight=1)
        ttk.Label(componentes, text='Base incluida: Python, Ollama, modelo LFM3 y herramientas académicas.', wraplength=660).grid(row=0, sticky='w', pady=(0, 8))
        filas = [
            ('escritorio', 'OpenCode Desktop', 'Habla con tu agente desde una aplicación. Requiere OpenCode CLI.'),
            ('obsidian', 'Obsidian', 'Abre tus apuntes y organiza tu carrera. La bóveda queda preconfigurada.'),
            ('opencode', 'OpenCode CLI', 'Usa el agente desde una terminal y habilita la aplicación Desktop.'),
            ('calibrar', 'Ajustar al rendimiento de mi equipo', 'Comprueba CPU, GPU y memoria para elegir la concurrencia.'),
        ]
        for i, (clave, titulo, detalle) in enumerate(filas):
            boton = ttk.Checkbutton(componentes, text=titulo, variable=self.opciones[clave],
                                    command=lambda k=clave: self.cambiar_opcion(k))
            boton.grid(row=i * 2 + 1, sticky='w', pady=(4, 0))
            ttk.Label(componentes, text=detalle, wraplength=640).grid(row=i * 2 + 2, sticky='w', padx=(24, 0), pady=(0, 5))
            self.controles.append(boton)

        ttk.Label(configuracion, text='Dónde se guardará', style='Seccion.TLabel').grid(row=1, sticky='w', pady=(19, 6))
        carpeta = ttk.Frame(configuracion)
        carpeta.grid(row=2, sticky='ew')
        carpeta.columnconfigure(0, weight=1)
        entrada = ttk.Entry(carpeta, textvariable=self.destino)
        entrada.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        entrada.bind('<FocusOut>', lambda _: self.cargar_preferencias())
        entrada.bind('<Return>', lambda _: self.cargar_preferencias())
        cambiar = ttk.Button(carpeta, text='Cambiar carpeta…', command=self.elegir_carpeta)
        cambiar.grid(row=0, column=1)
        self.controles.extend([entrada, cambiar])
        ttk.Label(configuracion, text='Tus asignaturas y apuntes permanecen en esta carpeta al actualizar.', wraplength=680).grid(row=3, sticky='w', pady=(7, 0))
        ttk.Label(configuracion, textvariable=self.resumen, wraplength=680).grid(row=4, sticky='w', pady=(4, 12))
        self.enlazar_desplazamiento(configuracion)
        ttk.Separator(principal).grid(row=7, sticky='ew', pady=(10, 0))
        ttk.Label(principal, textvariable=self.estado, wraplength=720).grid(row=8, sticky='w', pady=(12, 8))
        detalle = ttk.Frame(principal)
        detalle.grid(row=9, sticky='nsew')
        detalle.columnconfigure(0, weight=1)
        detalle.rowconfigure(0, weight=1)
        self.log = tk.Text(detalle, height=5, wrap='word', state='disabled', font=('TkFixedFont', 9), relief='solid', borderwidth=1)
        self.log.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(detalle, orient='vertical', command=self.log.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.log.configure(yscrollcommand=scroll.set)
        self.barra = ttk.Progressbar(principal, mode='indeterminate')
        self.barra.grid(row=10, sticky='ew', pady=(10, 10))
        acciones = ttk.Frame(principal)
        acciones.grid(row=11, sticky='ew')
        acciones.columnconfigure(0, weight=1)
        self.ver_archivos = ttk.Button(acciones, text='Abrir mis archivos', command=self.abrir_archivos)
        self.ver_archivos.grid(row=0, column=0, sticky='w')
        self.instalar = ttk.Button(acciones, text='Instalar selección', command=lambda: self.iniciar('preparar'))
        self.instalar.grid(row=0, column=1, padx=(8, 0))
        self.abrir = ttk.Button(acciones, text='Abrir mi agente', command=lambda: self.iniciar('iniciar'))
        self.abrir.grid(row=0, column=2, padx=(8, 0))
        self.controles.extend([self.ver_archivos, self.instalar, self.abrir])
        self.destino.trace_add('write', lambda *_: self.actualizar_resumen())
        self.actualizar_resumen()
        self._sondeo = ventana.after(100, self.recibir)
        ventana.bind('<Destroy>', self.detener_sondeo, add='+')

    def actualizar_resumen(self):
        proyecto = Path(self.destino.get()) / CARPETA
        existe = (proyecto / '.ufv-paquete.json').is_file()
        self.resumen.set('Instalación existente: se conservarán tus datos.' if existe else 'Primera instalación: necesita Internet y varios GB libres. No requiere permisos de administrador.')
        self.instalar.configure(text='Aplicar selección / actualizar' if existe else 'Instalar selección')
        self.abrir.configure(state='normal' if existe and not self.ocupado else 'disabled')
        self.ver_archivos.configure(state='normal' if (proyecto / 'boveda').is_dir() and not self.ocupado else 'disabled')

    def enlazar_desplazamiento(self, widget):
        widget.bind('<MouseWheel>', lambda e: self.lienzo.yview_scroll(-int(e.delta / 120) if abs(e.delta) >= 120 else (-1 if e.delta > 0 else 1), 'units'))
        widget.bind('<Button-4>', lambda _: self.lienzo.yview_scroll(-1, 'units'))
        widget.bind('<Button-5>', lambda _: self.lienzo.yview_scroll(1, 'units'))
        widget.bind('<FocusIn>', self.mostrar_foco, add='+')
        for hijo in widget.winfo_children():
            self.enlazar_desplazamiento(hijo)

    def mostrar_foco(self, evento):
        alto = self.lienzo.bbox('all')[3] if self.lienzo.bbox('all') else 1
        actual = self.lienzo.canvasy(0)
        y = evento.widget.winfo_rooty() - self.lienzo.winfo_rooty() + actual
        final = y + evento.widget.winfo_height()
        visible = self.lienzo.winfo_height()
        if y < actual:
            self.lienzo.yview_moveto(max(0, y - 6) / alto)
        elif final > actual + visible:
            self.lienzo.yview_moveto(max(0, final - visible + 6) / alto)

    def cambiar_opcion(self, clave):
        if clave == 'escritorio' and self.opciones[clave].get():
            self.opciones['opencode'].set(True)
        if clave == 'opencode' and not self.opciones[clave].get():
            self.opciones['escritorio'].set(False)

    def elegir_carpeta(self):
        ruta = filedialog.askdirectory(parent=self.ventana, title='Carpeta de Taller UFV', initialdir=self.destino.get(), mustexist=False)
        if ruta:
            self.destino.set(ruta)
            self.cargar_preferencias()

    def cargar_preferencias(self):
        try:
            for k, v in preferencias(self.destino.get()).items():
                self.opciones[k].set(v)
        except (OSError, ValueError) as error:
            messagebox.showerror('No se pudieron leer las preferencias', str(error), parent=self.ventana)

    def escribir(self, texto):
        self.log.configure(state='normal')
        self.log.insert('end', texto.rstrip() + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def iniciar(self, accion):
        if self.ocupado:
            return
        try:
            destino = validar_destino(self.destino.get())
            opciones = {k: v.get() for k, v in self.opciones.items()}
            destino.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=destino):
                pass
        except (ValueError, OSError) as error:
            messagebox.showerror('Revisa la carpeta de instalación', str(error), parent=self.ventana)
            return
        self.ocupado = True
        self.estado.set('Preparando la instalación… Puedes seguir el detalle aquí.')
        for control in self.controles:
            control.configure(state='disabled')
        self.barra.start(15)
        threading.Thread(target=self.trabajar, args=(destino, opciones, accion), daemon=True).start()

    def ejecutar(self, comando, proyecto):
        opciones = dict(cwd=proyecto, env=preparar_ambiente(), stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
        if sys.platform == 'win32':
            opciones['creationflags'] = subprocess.CREATE_NO_WINDOW
        self.proceso = subprocess.Popen(comando, **opciones)
        for linea in self.proceso.stdout:
            self.eventos.put(('log', linea))
        codigo = self.proceso.wait()
        self.proceso.stdout.close()
        self.proceso = None
        if codigo:
            raise RuntimeError(f'La preparación terminó con código {codigo}. Revisa el detalle y pulsa Reintentar.')

    def trabajar(self, destino, opciones, accion):
        try:
            proyecto = destino / CARPETA
            marcador = proyecto / '.ufv-paquete.json'
            instalado = json.loads(marcador.read_text(encoding='utf-8')) if marcador.is_file() else {}
            actualizado = False
            if instalado.get('sha256') != self.meta['sha256']:
                self.eventos.put(('estado', 'Descargando el paquete verificado de Taller UFV…'))
                with tempfile.TemporaryDirectory(prefix='ufv-descarga-') as temporal:
                    archivo = Path(temporal) / 'taller.zip'
                    with urlopen(Request(self.meta['url'], headers={'User-Agent': 'Taller-UFV-installer'}), timeout=90) as respuesta, archivo.open('wb') as salida:
                        total = 0
                        while bloque := respuesta.read(1024 * 1024):
                            salida.write(bloque)
                            total += len(bloque)
                        self.eventos.put(('log', f'Paquete descargado: {total // 1024} KB. Verificando SHA256…'))
                    proyecto = actualizar_paquete(archivo, destino, self.meta['sha256'], self.meta['version'])
                    actualizado = True
            if not instalacion_valida(proyecto, self.meta['sha256']):
                raise RuntimeError('La instalación contiene código modificado o archivos ausentes. Conserva esta carpeta y elige otra para reinstalar; tus apuntes siguen en boveda.')
            local = proyecto / '.local'
            local.mkdir(exist_ok=True)
            # Archivo de entrada separado: entorno guarda la selección sólo tras validarla.
            seleccion = local / 'seleccion-instalador.json'
            temporal = seleccion.with_suffix('.tmp')
            temporal.write_text(json.dumps(opciones, indent=2), encoding='utf-8')
            temporal.replace(seleccion)
            self.log_archivo = local / 'instalacion-ui.log'
            preparado = (local / 'ajustes.json').is_file() and (local / 'componentes.json').is_file()
            if accion == 'preparar' or actualizado or not preparado or opciones != preferencias(destino):
                self.eventos.put(('estado', 'Preparando los componentes elegidos. La primera vez puede tardar varios minutos.'))
                # Preparar primero evita arrancar un chat interactivo en una tubería invisible.
                self.ejecutar(comando_arranque(proyecto, 'preparar', seleccion), proyecto)
            if getattr(sys, 'frozen', False):
                crear_accesos(destino, Path(sys.executable))
            if accion == 'iniciar':
                configuracion = json.loads((local / 'ajustes.json').read_text(encoding='utf-8'))
                if opciones['escritorio'] and configuracion.get('interfaz') != 'terminal':
                    self.eventos.put(('estado', 'Abriendo tu agente y tus apuntes…'))
                    self.ejecutar(comando_arranque(proyecto, 'iniciar'), proyecto)
                else:
                    if opciones['escritorio']:
                        self.eventos.put(('estado', 'La prueba de OpenCode no terminó correctamente. Abrimos el agente Python en una terminal; consulta el registro para más detalle.'))
                    abrir_terminal(proyecto, None)
            self.eventos.put(('fin', 'Todo preparado. Abre tu agente ahora o vuelve desde el acceso Taller UFV.'))
        except Exception as error:
            self.eventos.put(('error', str(error)))

    def recibir(self):
        self.ventana.after_cancel(self._sondeo)
        try:
            while True:
                tipo, texto = self.eventos.get_nowait()
                if tipo == 'log':
                    self.escribir(texto)
                elif tipo == 'estado':
                    self.estado.set(texto)
                    self.escribir(texto)
                else:
                    self.ocupado = False
                    self.barra.stop()
                    for control in self.controles:
                        control.configure(state='normal')
                    self.actualizar_resumen()
                    self.estado.set(texto if tipo == 'fin' else 'No se ha completado. Corrige el problema y vuelve a intentarlo.')
                    self.escribir(texto)
                    if tipo == 'error':
                        self.instalar.configure(text='Reintentar instalación')
                    if self.log_archivo:
                        try:
                            self.log_archivo.write_text(self.log.get('1.0', 'end'), encoding='utf-8')
                        except OSError as error:
                            self.escribir(f'No se pudo guardar el registro: {error}')
        except queue.Empty:
            pass
        self._sondeo = self.ventana.after(100, self.recibir)

    def detener_sondeo(self, evento):
        if evento.widget is self.ventana:
            self.ventana.after_cancel(self._sondeo)

    def abrir_archivos(self):
        ruta = str(Path(self.destino.get()) / CARPETA / 'boveda')
        if sys.platform == 'win32':
            os.startfile(ruta)
        else:
            subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', ruta])

    def cerrar(self):
        if self.ocupado:
            messagebox.showinfo('Instalación en curso', 'Espera a que termine esta operación. El detalle muestra qué se está descargando o comprobando.', parent=self.ventana)
            return
        self.ventana.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', type=Path)
    parser.add_argument('--abrir', action='store_true')
    parser.add_argument('--prueba-ui', action='store_true', help='Prueba gráfica sin red ni cambios en la instalación.')
    parser.add_argument('--captura', type=Path)
    args = parser.parse_args()
    ventana = tk.Tk()
    try:
        meta = dict(version='prueba', sha256='0' * 64, url='https://example.invalid') if args.prueba_ui else metadata()
        # Las pruebas siempre usan una carpeta temporal, incluso si hay --destino.
        with tempfile.TemporaryDirectory(prefix='ufv-ui-') if args.prueba_ui else _sin_temporal() as temporal:
            app = Instalador(ventana, meta, Path(temporal) / 'Taller UFV' if temporal else args.destino)
            if args.prueba_ui:
                app.opciones['opencode'].set(False)
                app.cambiar_opcion('opencode')
                assert not app.opciones['escritorio'].get()
                app.opciones['escritorio'].set(True)
                app.cambiar_opcion('escritorio')
                assert app.opciones['opencode'].get()
                validar_destino(app.destino.get())
                if args.captura:
                    def capturar():
                        from PIL import ImageGrab
                        ventana.update_idletasks()
                        ImageGrab.grab(bbox=(ventana.winfo_rootx(), ventana.winfo_rooty(), ventana.winfo_rootx() + ventana.winfo_width(), ventana.winfo_rooty() + ventana.winfo_height())).save(args.captura)
                    ventana.after(600, capturar)
                ventana.after(1200, ventana.destroy)
            elif args.abrir:
                ventana.after(250, lambda: app.iniciar('iniciar'))
            ventana.mainloop()
        return 0
    except Exception as error:
        if not args.prueba_ui:
            messagebox.showerror('No se pudo abrir Taller UFV', str(error), parent=ventana)
        elif sys.stderr:
            print(str(error), file=sys.stderr)
        ventana.destroy()
        return 1


class _sin_temporal:
    def __enter__(self):
        return None

    def __exit__(self, *_):
        return False


if __name__ == '__main__':
    sys.exit(main())
