import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import subprocess
import pygame
import threading
from pathlib import Path
import queue

# -----------------------------
# Função para criar pastas necessárias
def create_required_folders():
    """Cria as pastas 'tools', 'images' e 'audio' no diretório do script, se não existirem."""
    folders = [Path("tools"), Path("images"), Path("audio")]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

# Cria as pastas necessárias ao iniciar o programa
create_required_folders()

# -----------------------------
# Funções do conversor
def select_bin_file():
    bin_path.set(filedialog.askopenfilename(title="Selecione o arquivo .bin", filetypes=[("BIN files", "*.bin")]))

def select_cue_file():
    cue_path.set(filedialog.askopenfilename(title="Selecione o arquivo .cue", filetypes=[("CUE files", "*.cue")]))

def select_output_folder():
    output_path.set(filedialog.askdirectory(title="Selecione a pasta de saída"))

def convert():
    bin_file = bin_path.get()
    cue_file = cue_path.get()
    out_folder = output_path.get()
    
    if not bin_file or not cue_file or not out_folder:
        messagebox.showwarning("Aviso", "Selecione todos os arquivos e pasta de saída!")
        return
    
    # Desativa o botão de converter para evitar múltiplas conversões
    convert_button.config(state="disabled")
    
    base_name = os.path.splitext(os.path.basename(bin_file))[0]
    cue2ccd_path = Path("tools/cue2ccd.exe")  # Caminho relativo para portabilidade
    
    if not cue2ccd_path.exists():
        messagebox.showerror("Erro", f"cue2ccd.exe não encontrado no caminho:\n{cue2ccd_path}\nPor favor, coloque o executável na pasta 'tools/'.")
        convert_button.config(state="normal")
        return

    # Tela de loading
    loading = tk.Toplevel(root)
    loading.title("Convertendo...")
    loading.geometry("400x100")
    loading_label = tk.Label(loading, text="Iniciando conversão...", font=("Arial", 12))
    loading_label.pack(pady=10)
    progress = ttk.Progressbar(loading, orient="horizontal", length=300, mode="indeterminate")
    progress.pack(pady=10)
    progress.start(10)  # Inicia animação indeterminada
    
    # Fila para atualizações seguras da interface
    progress_queue = queue.Queue()

    def run_conversion():
        try:
            # Executa cue2ccd
            process = subprocess.Popen(
                [str(cue2ccd_path), bin_file, cue_file, str(Path(out_folder) / base_name)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            for line in process.stdout:
                progress_queue.put(line.strip())  # Envia saída para a fila
            process.wait()
            progress_queue.put(None)  # Sinaliza conclusão
        except Exception as e:
            progress_queue.put(f"Erro: {e}")

    def check_queue():
        try:
            msg = progress_queue.get_nowait()
            if msg is None:
                loading.destroy()
                convert_button.config(state="normal")
                messagebox.showinfo("Sucesso", f"Conversão concluída!\nArquivos gerados na pasta {out_folder}")
            elif msg.startswith("Erro:"):
                loading.destroy()
                convert_button.config(state="normal")
                messagebox.showerror("Erro", msg)
            else:
                loading_label.config(text=f"Convertendo... {msg}")
                root.after(100, check_queue)
        except queue.Empty:
            root.after(100, check_queue)

    threading.Thread(target=run_conversion, daemon=True).start()
    root.after(100, check_queue)

# -----------------------------
# Função para tocar música
def play_music():
    music_file = Path("audio/phoenix_wright.mp3")  # Caminho relativo
    if music_file.exists():
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(str(music_file))
            pygame.mixer.music.play(loops=-1)
        except Exception as e:
            print(f"Falha ao tocar música: {e}")
    else:
        print(f"Arquivo de música não encontrado: {music_file}")

def stop_music():
    pygame.mixer.music.stop()

# -----------------------------
# Cleanup ao fechar
def on_closing():
    stop_music()
    pygame.mixer.quit()
    root.destroy()

# -----------------------------
# GUI
root = tk.Tk()
root.title("Conversor de BIN/CUE para IMG")
root.geometry("600x550")
root.configure(bg="black")
root.protocol("WM_DELETE_WINDOW", on_closing)

# Toca música
play_music()

# Variáveis de caminho
bin_path = tk.StringVar()
cue_path = tk.StringVar()
output_path = tk.StringVar()

# -----------------------------
# Canvas para logo e texto animado
canvas = tk.Canvas(root, width=600, height=200, bg="black", highlightthickness=0)
canvas.pack()

# Carrega logo do PS1
logo_path = Path("images/ps1_logo.png")  # Caminho relativo
try:
    logo_img = Image.open(logo_path).convert("RGBA")
    logo_img = logo_img.resize((150, int(150 * logo_img.height / logo_img.width)), Image.Resampling.LANCZOS)
    global logo_tk  # Evita que o coletor de lixo remova a imagem
    logo_tk = ImageTk.PhotoImage(logo_img)
    canvas.create_image(300, 100, image=logo_tk)
except Exception as e:
    print(f"Erro ao carregar imagem: {e}")

# Texto animado simplificado
logo_text = "Conversor de BIN/CUE para IMG"
colors = ["#FFFFFF", "#FFD700", "#FFFF00"]
color_index = 0

def update_logo():
    global color_index  # Usa a variável global
    color_index = (color_index + 1) % len(colors)
    canvas.delete("logo_text")
    canvas.create_text(300, 180, text=logo_text, fill=colors[color_index], font=("Arial", 22, "bold"), tags="logo_text")
    root.after(500, update_logo)

update_logo()

# -----------------------------
# Interface de seleção de arquivos
frame = tk.Frame(root, bg="black")
frame.pack(pady=10)

tk.Label(frame, text="Arquivo BIN:", fg="white", bg="black").grid(row=0, column=0, sticky="w")
tk.Entry(frame, textvariable=bin_path, width=40).grid(row=0, column=1, padx=5)
tk.Button(frame, text="Selecionar BIN", command=select_bin_file).grid(row=0, column=2, padx=5)

tk.Label(frame, text="Arquivo CUE:", fg="white", bg="black").grid(row=1, column=0, sticky="w", pady=5)
tk.Entry(frame, textvariable=cue_path, width=40).grid(row=1, column=1, padx=5)
tk.Button(frame, text="Selecionar CUE", command=select_cue_file).grid(row=1, column=2, padx=5)

tk.Label(frame, text="Pasta de saída:", fg="white", bg="black").grid(row=2, column=0, sticky="w")
tk.Entry(frame, textvariable=output_path, width=40).grid(row=2, column=1, padx=5)
tk.Button(frame, text="Selecionar pasta", command=select_output_folder).grid(row=2, column=2, padx=5)

# Botão de converter
convert_button = tk.Button(root, text="Converter", command=convert, bg="green", fg="white", width=20)
convert_button.pack(pady=10)

# Botão de parar música
tk.Button(root, text="Parar Música", command=stop_music, bg="red", fg="white", width=20).pack(pady=5)

root.mainloop()