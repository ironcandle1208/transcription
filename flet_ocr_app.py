import flet as ft
from PIL import Image
import pytesseract
import os
import threading
import time

# Tesseract-OCRのパス設定（Windowsでパスが通っていない場合）
# ご自身の環境に合わせてパスを修正し、コメントを解除してください。
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class OcrApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.filepaths = []
        
        # --- File Pickers ---
        self.file_picker = ft.FilePicker(on_result=self.on_open_result)
        self.save_file_picker = ft.FilePicker(on_result=self.on_save_result)
        page.overlay.extend([self.file_picker, self.save_file_picker])

        # --- UI Controls ---
        self.select_button = ft.ElevatedButton(
            "画像ファイルを選択",
            on_click=lambda _: self.file_picker.pick_files(
                allow_multiple=True,
                allowed_extensions=["png", "jpg", "jpeg", "bmp", "gif", "tiff"]
            ),
        )
        self.run_button = ft.ElevatedButton("文字起こし実行", on_click=self.run_ocr, disabled=True)
        self.save_button = ft.ElevatedButton("テキストを保存", on_click=self.save_text, disabled=True)
        self.file_label = ft.Text("ファイルが選択されていません")
        self.text_area = ft.TextField(
            multiline=True,
            read_only=True,
            expand=True,
            min_lines=15,
        )
        
        # --- Main Layout ---
        self.layout = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        self.select_button,
                        self.run_button,
                        self.save_button,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                ),
                ft.Row(controls=[self.file_label], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(controls=[self.text_area], expand=True),
            ],
            expand=True,
        )

    def on_open_result(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.filepaths = sorted([f.path for f in e.files], key=os.path.basename)
            self.file_label.value = f"{len(self.filepaths)}個のファイルを選択中"
            self.run_button.disabled = False
            self.save_button.disabled = True
            self.text_area.value = ""
        else:
            self.filepaths = []
            self.file_label.value = "ファイルが選択されていません"
            self.run_button.disabled = True
        self.page.update()

    def ocr_worker(self):
        try:
            full_text = ""
            total_files = len(self.filepaths)
            for i, filepath in enumerate(self.filepaths):
                filename = os.path.basename(filepath)
                header = f"--- [{i+1}/{total_files}] {filename} の文字起こし結果 ---\n"
                full_text += header
                try:
                    img = Image.open(filepath)
                    text = pytesseract.image_to_string(img, lang='jpn+eng')
                    full_text += text + "\n\n"
                except Exception as e:
                    full_text += f"処理中にエラーが発生しました: {e}\n\n"
                self.text_area.value = full_text
                self.page.update()

            full_text += "--- 全ての処理が完了しました ---\n"
            self.text_area.value = full_text
        except Exception as e:
            self.text_area.value += f"OCRワーカーで予期せぬエラーが発生しました: {e}\n\n"
        finally:
            self.run_button.disabled = False
            self.select_button.disabled = False
            if self.text_area.value.strip():
                self.save_button.disabled = False
            self.page.update()

    def run_ocr(self, e):
        if not self.filepaths:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("先に画像ファイルを選択してください。"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        self.run_button.disabled = True
        self.select_button.disabled = True
        self.save_button.disabled = True
        self.text_area.value = ""
        self.page.update()

        thread = threading.Thread(target=self.ocr_worker, daemon=True)
        thread.start()

    def save_text(self, e):
        content = self.text_area.value.strip()
        if not content:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("保存するテキストがありません。"))
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        self.save_file_picker.save_file(
            dialog_title="テキストを保存",
            file_name="transcription.txt",
            allowed_extensions=["txt"],
        )

    def on_save_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            try:
                with open(e.path, 'w', encoding='utf-8') as file:
                    file.write(self.text_area.value.strip())
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"ファイルを保存しました: {e.path}"))
            except Exception as err:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"ファイルの保存中にエラーが発生しました: {err}"))
            
            self.page.snack_bar.open = True
            self.page.update()

def main(page: ft.Page):
    page.title = "Flet 画像文字起こしアプリ"
    page.window_width = 700
    page.window_height = 550
    
    app = OcrApp(page)
    page.add(app.layout)

if __name__ == "__main__":
    ft.app(target=main)
