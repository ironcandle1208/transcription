import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image
import pytesseract
import os
import threading
import queue

# --- 関数定義 ---

def select_file():
    """ファイル選択ダイアログを開き、選択されたファイルのパスをグローバル変数に格納する"""
    global filepaths
    # ファイルダイアログを開いて複数の画像ファイルを選択させる
    # askopenfilenames はファイルパスのタプルを返す
    # 返り値はタプルなのでリストに変換してソートする
    selected_paths = filedialog.askopenfilenames(
        filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff")]
    )
    if selected_paths:
        # ファイル名を基準に昇順でソートする
        filepaths = sorted(list(selected_paths), key=os.path.basename)
        # 選択されたファイル数を表示
        file_label.config(text=f"{len(filepaths)}個のファイルを選択中")
        # 実行ボタンを有効化
        run_button.config(state=tk.NORMAL)
        # 保存ボタンは無効化
        save_button.config(state=tk.DISABLED)
        # テキストエリアをクリア
        text_area.delete(1.0, tk.END)

def _ocr_worker(filepaths_to_process, q):
    """OCR処理をバックグラウンドで実行するワーカー関数"""
    try:
        total_files = len(filepaths_to_process)
        for i, filepath in enumerate(filepaths_to_process):
            filename = os.path.basename(filepath)
            
            # ファイルごとのヘッダーをキューに追加
            header = f"--- [{i+1}/{total_files}] {filename} の文字起こし結果 ---\n"
            q.put(("progress", header))

            try:
                # OCRの実行
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img, lang='jpn+eng')
                
                # 結果をキューに追加
                q.put(("result", text + "\n\n"))

            except Exception as e:
                error_message = f"処理中にエラーが発生しました: {e}\n\n"
                q.put(("error", error_message))
                continue
        
        # 処理完了のシグナルをキューに追加
        q.put(("done", None))

    except Exception as e:
        # ワーカー処理全体での予期せぬエラー
        q.put(("error", f"OCRワーカーで予期せぬエラーが発生しました: {e}\n\n"))
        q.put(("done", None))

def _process_queue(q):
    """キューを定期的にチェックしてUIを更新する"""
    try:
        message_type, data = q.get_nowait()
        if message_type == "done":
            text_area.insert(tk.END, "--- 全ての処理が完了しました ---\n")
            run_button.config(state=tk.NORMAL)
            select_button.config(state=tk.NORMAL)
            if text_area.get(1.0, tk.END).strip():
                save_button.config(state=tk.NORMAL)
            return # ポーリングを停止
        else:
            # 'progress', 'result', 'error' のいずれか
            text_area.insert(tk.END, data)
            text_area.see(tk.END) # テキストエリアの末尾にスクロール
    except queue.Empty:
        pass # キューが空の場合は何もしない
    finally:
        # 100ミリ秒後にもう一度自身を呼び出す
        root.after(100, _process_queue, q)

def run_ocr():
    """OCR処理のスレッドを開始し、UIの応答性を維持する"""
    if not filepaths:
        messagebox.showwarning("警告", "先に画像ファイルを選択してください。")
        return

    # 処理中にボタンを無効化
    run_button.config(state=tk.DISABLED)
    select_button.config(state=tk.DISABLED)
    save_button.config(state=tk.DISABLED)
    text_area.delete(1.0, tk.END)

    # スレッド間通信のためのキューを作成
    q = queue.Queue()
    # OCR処理を別スレッドで実行
    thread = threading.Thread(target=_ocr_worker, args=(filepaths, q), daemon=True)
    thread.start()

    # キューのポーリングを開始してUIを更新
    _process_queue(q)

def save_text_to_file():
    """テキストエリアの内容をテキストファイルに保存する"""
    # テキストエリアから内容を取得（末尾の不要な改行を削除）
    content = text_area.get(1.0, tk.END).strip()
    if not content:
        messagebox.showwarning("警告", "保存するテキストがありません。")
        return

    # 保存ダイアログを開く
    save_filepath = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
        title="テキストを保存"
    )

    # ファイルパスが選択された場合（キャンセルされなかった場合）
    if save_filepath:
        try:
            with open(save_filepath, 'w', encoding='utf-8') as file:
                file.write(content)
            messagebox.showinfo("成功", f"ファイルを保存しました: {save_filepath}")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの保存中にエラーが発生しました: {e}")

# --- GUIのセットアップ ---

# グローバル変数でファイルパスを保持
filepaths = []

# Tesseract-OCRのパス設定（Windowsでパスが通っていない場合）
# ご自身の環境に合わせてパスを修正し、コメントを解除してください。
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# メインウィンドウ
root = tk.Tk()
root.title("Tkinter 画像文字起こしアプリ")
root.geometry("700x500")

# 上部のフレーム（ボタンとラベル用）
top_frame = tk.Frame(root, pady=10)
top_frame.pack()

select_button = tk.Button(top_frame, text="画像ファイルを選択", command=select_file)
select_button.pack(side=tk.LEFT, padx=10)

run_button = tk.Button(top_frame, text="文字起こし実行", command=run_ocr, state=tk.DISABLED)
run_button.pack(side=tk.LEFT, padx=10)

save_button = tk.Button(top_frame, text="テキストを保存", command=save_text_to_file, state=tk.DISABLED)
save_button.pack(side=tk.LEFT, padx=10)

file_label = tk.Label(top_frame, text="ファイルが選択されていません")
file_label.pack(side=tk.LEFT, padx=10)

text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Meiryo UI", 10))
text_area.pack(expand=True, fill='both', padx=10, pady=10)

root.mainloop()
