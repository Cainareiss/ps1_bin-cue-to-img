import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
from pathlib import Path
import pygame
import threading
import queue
import shutil

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
# Função para validar arquivos .bin e .cue
def validate_bin_cue(bin_file, cue_file):
    """Valida se os arquivos .bin e .cue são compatíveis e se o .bin referenciado existe."""
    if not bin_file or not cue_file:
        return False, "Selecione ambos os arquivos .bin e .cue."
    
    # Verifica se os arquivos têm o mesmo nome base
    bin_base = os.path.splitext(os.path.basename(bin_file))[0]
    cue_base = os.path.splitext(os.path.basename(cue_file))[0]
    if bin_base != cue_base:
        return False, "Os arquivos .bin e .cue devem ter o mesmo nome base."
    
    # Verifica se o arquivo .bin referenciado no .cue existe
    try:
        with open(cue_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('FILE'):
                    bin_name = line.split('"')[1]  # Extrai o nome do arquivo .bin do .cue
                    bin_path = Path(os.path.dirname(cue_file)) / bin_name
                    if not bin_path.exists():
                        return False, f"O arquivo .bin referenciado no .cue ('{bin_name}') não foi encontrado."
        return True, ""
    except Exception as e:
        return False, f"Erro ao ler o arquivo .cue: {e}"

# -----------------------------
# Função para converter .bin/.cue para .img
def convert_to_img(bin_file, cue_file, output_folder):
    """Converte o arquivo .bin para .img com base no .cue."""
    try:
        # Lê o arquivo .cue para obter o nome do .bin
        bin_name = None
        with open(cue_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('FILE'):
                    bin_name = line.split('"')[1]
                    break
        if not bin_name:
            return False, "Nenhum arquivo .bin encontrado no .cue."
        
        # Verifica se o .bin referenciado existe
        bin_path = Path(os.path.dirname(cue_file)) / bin_name
        if not bin_path.exists():
            return False, f"Arquivo .bin referenciado ('{bin_name}') não encontrado."
        
        # Nome do arquivo de saída
        base_name = os.path.splitext(os.path.basename(cue_file))[0]
        output_img = Path(output_folder) / f"{base_name}.img"
        
        # Copia o conteúdo do .bin para .img
        shutil.copyfile(bin_path, output_img)
        return True, f"Conversão concluída! Arquivo gerado: {output_img}"
    except Exception as e:
        return False, f"Erro durante a conversão: {e}"

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
    
    # Valida arquivos
    is_valid, error_msg = validate_bin_cue(bin_file, cue_file)
    if not is_valid:
        messagebox.showwarning("Aviso", error_msg)
        return
    
    if not out_folder:
        messagebox.showwarning("Aviso", "Selecione a pasta de saída!")
        return
    
    # Desativa o botão de converter para evitar múltiplas conversões
    convert_button.config(state="disabled")
    
    # Tela de loading
    loading = tk.Toplevel(root)
    loading.title("Convertendo...")
    loading.geometry("400x100")
    loading_label = tk.Label(loading, text="Iniciando conversão...", font=("Arial", 12))
    loading_label.pack(pady=10)
    progress = ttk.Progressbar(loading, orient="horizontal", length=300, mode="determinate")
    progress.pack(pady=10)
    
    # Fila para atualizações seguras da interface
    progress_queue = queue.Queue()

    def run_conversion():
        try:
            # Tamanho do arquivo para a barra de progresso
            bin_size = os.path.getsize(bin_file)
            chunk_size = 1024 * 1024  # 1 MB
            copied_size = 0
            
            # Executa a conversão
            success, msg = convert_to_img(bin_file, cue_file, out_folder)
            if success:
                copied_size = bin_size  # Simula conclusão
                progress_queue.put((100, msg))  # Envia progresso e mensagem
            else:
                progress_queue.put((0, msg))  # Envia erro
        except Exception as e:
            progress_queue.put((0, f"Erro: {e}"))

    def check_queue():
        try:
            percent, msg = progress_queue.get_nowait()
            progress["value"] = percent
            loading_label.config(text=msg)
            if percent == 100 or msg.startswith("Erro:"):
                loading.destroy()
                convert_button.config(state="normal")
                if percent == 100:
                    messagebox.showinfo("Sucesso", msg)
                else:
                    messagebox.showerror("Erro", msg)
            else:
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
