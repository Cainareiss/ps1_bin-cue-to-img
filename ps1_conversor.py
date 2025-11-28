import tkinter as tk
from tkinter import filedialog, messagebox, ttk, Listbox
from PIL import Image, ImageTk
import os
from pathlib import Path
import pygame
import threading
import queue
import shutil
import re

# -----------------------------
# Função para criar pastas necessárias
def create_required_folders():
    """Cria as pastas 'images' e 'audio' no diretório do script, se não existirem."""
    folders = [Path("images"), Path("audio")]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

# Cria as pastas necessárias ao iniciar o programa
create_required_folders()

# -----------------------------
# Funções de controle de música
music_folder = Path("audio")  # Caminho relativo para maior portabilidade
music_list = []
current_music_index = -1
music_paused = False

def load_music_list():
    """Carrega a lista de arquivos .mp3 da pasta especificada."""
    global music_list
    music_list = []
    if music_folder.exists():
        music_list = list(music_folder.glob("*.mp3"))
        if not music_list:
            print(f"Nenhum arquivo .mp3 encontrado em {music_folder}")
    else:
        print(f"Pasta de áudio não encontrada: {music_folder}")
    update_music_label()

def select_music():
    """Abre uma janela para selecionar uma música da lista."""
    if not music_list:
        messagebox.showinfo("Aviso", f"Nenhum arquivo .mp3 encontrado em {music_folder}")
        return
    
    music_window = tk.Toplevel(root)
    music_window.title("Selecionar Música")
    music_window.geometry("400x300")
    music_window.configure(bg="black")
    
    tk.Label(music_window, text="Selecione uma música:", fg="white", bg="black", font=("Arial", 12)).pack(pady=10)
    
    listbox = Listbox(music_window, width=50, height=10, bg="black", fg="white", selectbackground="blue")
    for music in music_list:
        listbox.insert(tk.END, music.name)
    listbox.pack(pady=10)
    
    def on_select():
        global current_music_index
        selection = listbox.curselection()
        if selection:
            current_music_index = selection[0]
            play_music()
            music_window.destroy()
    
    tk.Button(music_window, text="Selecionar", command=on_select, bg="green", fg="white").pack(pady=10)

def play_music():
    """Toca ou retoma a música atual."""
    global music_paused
    if music_list and current_music_index >= 0:
        music_file = music_list[current_music_index]
        if music_file.exists():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                if music_paused:
                    pygame.mixer.music.unpause()
                    music_paused = False
                    play_pause_button.config(text="Pausar")
                else:
                    pygame.mixer.music.load(str(music_file))
                    pygame.mixer.music.play(loops=-1)
                    play_pause_button.config(text="Pausar")
                    update_music_label()
            except Exception as e:
                print(f"Falha ao tocar música: {e}")
        else:
            print(f"Arquivo de música não encontrado: {music_file}")

def toggle_play_pause():
    """Alterna entre pausar e resumir a música."""
    global music_paused
    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        if music_paused:
            pygame.mixer.music.unpause()
            music_paused = False
            play_pause_button.config(text="Pausar")
        else:
            pygame.mixer.music.pause()
            music_paused = True
            play_pause_button.config(text="Tocar")
    else:
        play_music()

def next_music():
    """Toca a próxima música na lista."""
    global current_music_index
    if music_list:
        current_music_index = (current_music_index + 1) % len(music_list)
        play_music()

def previous_music():
    """Toca a música anterior na lista."""
    global current_music_index
    if music_list:
        current_music_index = (current_music_index - 1) % len(music_list)
        play_music()

def stop_music():
    """Para a reprodução de música."""
    global music_paused
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        music_paused = False
        play_pause_button.config(text="Tocar")

def update_music_label():
    """Atualiza o rótulo com o nome da música atual."""
    if music_list and current_music_index >= 0:
        music_label.config(text=f"Tocando: {music_list[current_music_index].name}")
    else:
        music_label.config(text="Nenhuma música selecionada")

# -----------------------------
# Função para parsear o arquivo .cue
def parse_cue_file(cue_file):
    """Lê o arquivo .cue e retorna uma lista de arquivos .bin e informações de faixas."""
    try:
        bin_files = []
        tracks = []
        current_track = None
        with open(cue_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('FILE'):
                    bin_name = line.split('"')[1]
                    bin_files.append(bin_name)
                elif line.startswith('TRACK'):
                    track_num = int(re.search(r'\d+', line).group())
                    track_type = line.split()[-1]
                    current_track = {'number': track_num, 'type': track_type, 'indexes': []}
                    tracks.append(current_track)
                elif line.startswith('INDEX') and current_track:
                    index_num, timestamp = re.search(r'INDEX\s+(\d+)\s+(\d+:\d+:\d+)', line).groups()
                    current_track['indexes'].append({'number': int(index_num), 'timestamp': timestamp})
        # Valida índices de faixas
        for i, track in enumerate(tracks):
            if track['indexes']:
                timestamp = track['indexes'][0]['timestamp']
                min, sec, frame = map(int, timestamp.split(':'))
                total_frames = (min * 60 + sec) * 75 + frame
                if total_frames < 0 or (i > 0 and total_frames <= tracks[i-1]['indexes'][0]['total_frames']):
                    return [], [], "Erro: Índices de faixas inválidos ou fora de ordem"
                track['indexes'][0]['total_frames'] = total_frames
        return bin_files, tracks, ""
    except FileNotFoundError:
        return [], [], "Erro: Arquivo .cue não encontrado."
    except Exception as e:
        return [], [], f"Erro ao parsear o arquivo .cue: {e}"

# -----------------------------
# Função para validar arquivos .bin e .cue
def validate_bin_cue(bin_file, cue_file):
    """Valida se os arquivos .bin e .cue são compatíveis e se os .bin referenciados existem."""
    if not bin_file or not cue_file:
        return False, "Selecione pelo menos um arquivo .bin e .cue."
    
    bin_base = os.path.splitext(os.path.basename(bin_file))[0]
    cue_base = os.path.splitext(os.path.basename(cue_file))[0]
    if bin_base != cue_base:
        return False, "Os arquivos .bin e .cue devem ter o mesmo nome base."
    
    bin_files, tracks, error = parse_cue_file(cue_file)
    if error:
        return False, error
    
    if not bin_files:
        return False, "Nenhum arquivo .bin encontrado no .cue."
    
    cue_dir = Path(os.path.dirname(cue_file))
    for bin_name in bin_files:
        bin_path = cue_dir / bin_name
        if not bin_path.exists():
            return False, f"O arquivo .bin referenciado no .cue ('{bin_name}') não foi encontrado."
    
    return True, ""

# -----------------------------
# Função para converter .bin/.cue para .img, .ccd e, se disponível, .sub
def convert_to_img_ccd_sub(bin_file, cue_file, output_folder):
    """Converte o arquivo .bin/.cue para .img, .ccd e, se existir, copia .sub."""
    try:
        cue_dir = Path(os.path.dirname(cue_file))
        base_name = os.path.splitext(os.path.basename(cue_file))[0]
        output_img = Path(output_folder) / f"{base_name}.img"
        output_ccd = Path(output_folder) / f"{base_name}.ccd"
        output_sub = Path(output_folder) / f"{base_name}.sub"
        
        # Parseia o .cue
        bin_files, tracks, error = parse_cue_file(cue_file)
        if error:
            return False, error
        
        # Concatena .bin em .img
        total_size = sum(os.path.getsize(cue_dir / bin_name) for bin_name in bin_files)
        chunk_size = 1024 * 1024  # 1 MB
        copied_size = 0
        
        with open(output_img, 'wb') as img_file:
            for bin_name in bin_files:
                bin_path = cue_dir / bin_name
                with open(bin_path, 'rb') as bin_f:
                    while True:
                        chunk = bin_f.read(chunk_size)
                        if not chunk:
                            break
                        img_file.write(chunk)
                        copied_size += len(chunk)
                        yield (copied_size / total_size * 50.0, f"Convertendo {base_name}.img... {(copied_size / total_size * 100):.1f}%")
        
        # Gera o .ccd
        yield (50.0, f"Gerando {base_name}.ccd...")
        with open(output_ccd, 'w', encoding='utf-8') as ccd_file:
            ccd_file.write("[CloneCD]\n")
            ccd_file.write("Version=3\n")
            ccd_file.write("[Disc]\n")
            ccd_file.write(f"TocEntries={len(tracks)}\n")
            ccd_file.write("Sessions=1\n")
            ccd_file.write("DataTracksScrambled=0\n")
            ccd_file.write("CDTextLength=0\n")
            
            for track in tracks:
                ccd_file.write(f"[Entry {track['number']-1}]\n")
                ccd_file.write(f"Session=1\n")
                ccd_file.write(f"Point={track['number']}\n")
                ccd_file.write(f"ADR=1\n")
                ccd_file.write(f"Control=4\n")
                ccd_file.write(f"TrackNo=0\n")
                ccd_file.write(f"AMin=0\n")
                ccd_file.write(f"ASec=0\n")
                ccd_file.write(f"AFrame=0\n")
                ccd_file.write(f"ALBA=-150\n")
                ccd_file.write(f"Zero=0\n")
                ccd_file.write(f"PMin={track['indexes'][0]['timestamp'].split(':')[0]}\n")
                ccd_file.write(f"PSec={track['indexes'][0]['timestamp'].split(':')[1]}\n")
                ccd_file.write(f"PFrame={track['indexes'][0]['timestamp'].split(':')[2]}\n")
                ccd_file.write(f"PLBA=0\n")
        
        # Copia o .sub, se existir
        sub_file = cue_dir / f"{base_name}.sub"
        if sub_file.exists():
            yield (75.0, f"Copiando {base_name}.sub...")
            shutil.copyfile(sub_file, output_sub)
            yield (100, f"Conversão concluída! Arquivos gerados: {output_img}, {output_ccd}, {output_sub}")
            return True, f"Conversão concluída! Arquivos gerados: {output_img}, {output_ccd}, {output_sub}"
        else:
            yield (100, f"Conversão concluída! Arquivos gerados: {output_img}, {output_ccd} (nenhum .sub encontrado)")
            return True, f"Conversão concluída! Arquivos gerados: {output_img}, {output_ccd} (nenhum .sub encontrado)"
    
    except PermissionError:
        return False, "Erro: Permissão negada ao escrever arquivos na pasta de saída."
    except FileNotFoundError:
        return False, "Erro: Arquivo .bin ou .cue não encontrado."
    except Exception as e:
        return False, f"Erro durante a conversão: {e}"

# -----------------------------
# Funções do conversor
def select_bin_cue_files():
    """Permite selecionar múltiplos arquivos .cue e associa os .bin correspondentes."""
    cue_files = filedialog.askopenfilenames(title="Selecione arquivos .cue", filetypes=[("CUE files", "*.cue")])
    valid_pairs = []
    for cue_file in cue_files:
        cue_base = os.path.splitext(os.path.basename(cue_file))[0]
        cue_dir = os.path.dirname(cue_file)
        bin_file = os.path.join(cue_dir, f"{cue_base}.bin")
        is_valid, error_msg = validate_bin_cue(bin_file, cue_file)
        if is_valid:
            valid_pairs.append((bin_file, cue_file))
        else:
            messagebox.showwarning("Aviso", f"Falha ao validar {cue_file}: {error_msg}")
    bin_cue_pairs.set(valid_pairs)
    update_file_list()

def update_file_list():
    """Atualiza a lista de arquivos selecionados na GUI."""
    file_listbox.delete(0, tk.END)
    for bin_file, cue_file in bin_cue_pairs.get():
        file_listbox.insert(tk.END, f"{os.path.basename(cue_file)}")

def select_output_folder():
    output_path.set(filedialog.askdirectory(title="Selecione a pasta de saída"))

def convert():
    pairs = bin_cue_pairs.get()
    out_folder = output_path.get()
    
    if not pairs:
        messagebox.showwarning("Aviso", "Selecione pelo menos um par de arquivos .bin/.cue!")
        return
    
    if not out_folder:
        messagebox.showwarning("Aviso", "Selecione a pasta de saída!")
        return
    
    convert_button.config(state="disabled")
    
    loading = tk.Toplevel(root)
    loading.title("Convertendo...")
    loading.geometry("400x100")
    loading_label = tk.Label(loading, text="Iniciando conversão...", font=("Arial", 12))
    loading_label.pack(pady=10)
    progress = ttk.Progressbar(loading, orient="horizontal", length=300, mode="determinate")
    progress.pack(pady=10)
    
    progress_queue = queue.Queue()
    total_files = len(pairs)
    converted_files = 0

    def run_conversion():
        nonlocal converted_files
        try:
            for i, (bin_file, cue_file) in enumerate(pairs, 1):
                for percent, msg in convert_to_img_ccd_sub(bin_file, cue_file, out_folder):
                    adjusted_percent = (converted_files + percent / 100) / total_files * 100
                    progress_queue.put((adjusted_percent, f"[{i}/{total_files}] {msg}"))
                success, final_msg = progress_queue.get()
                progress_queue.put((success and (converted_files + 1) / total_files * 100 or converted_files / total_files * 100, final_msg))
                if success:
                    converted_files += 1
        except Exception as e:
            progress_queue.put((converted_files / total_files * 100, f"Erro: {e}"))

    def check_queue():
        try:
            percent, msg = progress_queue.get_nowait()
            progress["value"] = percent
            loading_label.config(text=msg)
            if percent >= 100 or msg.startswith("Erro:"):
                loading.destroy()
                convert_button.config(state="normal")
                if percent >= 100:
                    messagebox.showinfo("Sucesso", f"Conversão concluída para {converted_files}/{total_files} arquivos!")
                    if output_path.get():
                        os.startfile(output_path.get())  # Abre a pasta de saída
                else:
                    messagebox.showerror("Erro", msg)
            else:
                root.after(100, check_queue)
        except queue.Empty:
            root.after(100, check_queue)

    threading.Thread(target=run_conversion, daemon=True).start()
    root.after(100, check_queue)

# -----------------------------
# Cleanup ao fechar
def on_closing():
    stop_music()
    pygame.mixer.quit()
    root.destroy()

# -----------------------------
# GUI
root = tk.Tk()
root.title("Conversor de BIN/CUE para IMG/CCD/SUB")
root.geometry("600x600")
root.configure(bg="black")
root.protocol("WM_DELETE_WINDOW", on_closing)

# Variáveis de caminho
bin_cue_pairs = tk.Variable()  # Lista de pares (bin, cue)
output_path = tk.StringVar()

# Canvas para logo e texto animado
canvas = tk.Canvas(root, width=600, height=200, bg="black", highlightthickness=0)
canvas.pack()

# Carrega logo do PS1
logo_path = Path("images/ps1_logo.png")
try:
    logo_img = Image.open(logo_path).convert("RGBA")
    logo_img = logo_img.resize((150, int(150 * logo_img.height / logo_img.width)), Image.Resampling.LANCZOS)
    global logo_tk
    logo_tk = ImageTk.PhotoImage(logo_img)
    canvas.create_image(300, 100, image=logo_tk)
except Exception as e:
    print(f"Erro ao carregar imagem: {e}")

# Texto animado
logo_text = "Conversor de BIN/CUE para IMG/CCD/SUB"
colors = ["#FFFFFF", "#FFD700", "#FFFF00"]
color_index = 0

def update_logo():
    global color_index
    color_index = (color_index + 1) % len(colors)
    canvas.delete("logo_text")
    canvas.create_text(300, 180, text=logo_text, fill=colors[color_index], font=("Arial", 22, "bold"), tags="logo_text")
    root.after(500, update_logo)

update_logo()

# Interface de seleção de arquivos
frame = tk.Frame(root, bg="black")
frame.pack(pady=10)

tk.Label(frame, text="Arquivos BIN/CUE:", fg="white", bg="black", font=("Arial", 10)).grid(row=0, column=0, sticky="w")
file_listbox = Listbox(frame, width=40, height=5, bg="black", fg="white", selectbackground="blue")
file_listbox.grid(row=0, column=1, padx=5)
# Ícone para botão de seleção
select_icon_path = Path("images/select_icon.png")
select_icon = None
if select_icon_path.exists():
    select_icon_img = Image.open(select_icon_path).resize((20, 20), Image.Resampling.LANCZOS)
    select_icon = ImageTk.PhotoImage(select_icon_img)
select_button = ttk.Button(frame, text="Selecionar Arquivos", image=select_icon, compound="left", command=select_bin_cue_files)
select_button.image = select_icon  # Evita garbage collection
select_button.grid(row=0, column=2, padx=5)

tk.Label(frame, text="Pasta de saída:", fg="white", bg="black", font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
tk.Entry(frame, textvariable=output_path, width=40).grid(row=1, column=1, padx=5)
output_icon_path = Path("images/folder_icon.png")
output_icon = None
if output_icon_path.exists():
    output_icon_img = Image.open(output_icon_path).resize((20, 20), Image.Resampling.LANCZOS)
    output_icon = ImageTk.PhotoImage(output_icon_img)
output_button = ttk.Button(frame, text="Selecionar Pasta", image=output_icon, compound="left", command=select_output_folder)
output_button.image = output_icon
output_button.grid(row=1, column=2, padx=5)

# Botão de converter
convert_icon_path = Path("images/convert_icon.png")
convert_icon = None
if convert_icon_path.exists():
    convert_icon_img = Image.open(convert_icon_path).resize((20, 20), Image.Resampling.LANCZOS)
    convert_icon = ImageTk.PhotoImage(convert_icon_img)
convert_button = ttk.Button(root, text="Converter", image=convert_icon, compound="left", command=convert)
convert_button.image = convert_icon
convert_button.pack(pady=10)

# Frame para controles de música
music_frame = tk.Frame(root, bg="black")
music_frame.pack(pady=10)

tk.Button(music_frame, text="Selecionar Música", command=select_music, bg="blue", fg="white").grid(row=0, column=0, padx=5)
play_pause_button = tk.Button(music_frame, text="Tocar", command=toggle_play_pause, bg="blue", fg="white")
play_pause_button.grid(row=0, column=1, padx=5)
tk.Button(music_frame, text="Anterior", command=previous_music, bg="blue", fg="white").grid(row=0, column=2, padx=5)
tk.Button(music_frame, text="Próxima", command=next_music, bg="blue", fg="white").grid(row=0, column=3, padx=5)
tk.Button(music_frame, text="Parar Música", command=stop_music, bg="red", fg="white").grid(row=0, column=4, padx=5)
music_label = tk.Label(music_frame, text="Nenhuma música selecionada", fg="white", bg="black", font=("Arial", 10))
music_label.grid(row=1, column=0, columnspan=5, pady=5)

# Carrega a lista de músicas e tenta tocar a primeira
load_music_list()
if music_list:
    current_music_index = 0
    play_music()

root.mainloop()