import pytest
from unittest.mock import MagicMock, patch
import os

# Fletとアプリケーションのモジュールをインポート
# Fletのコア機能もモックする必要がある場合がある
with patch('flet.app') as mock_flet_app:
    from flet_ocr_app import OcrApp

@pytest.fixture
def mock_page():
    """FletのPageオブジェクトのモックを作成する"""
    page = MagicMock()
    page.overlay = []
    page.update = MagicMock()
    page.snack_bar = MagicMock()
    return page

@pytest.fixture
def app(mock_page):
    """テスト対象のOcrAppインスタンスを作成する"""
    return OcrApp(mock_page)

def test_initial_state(app):
    """アプリケーションの初期状態をテストする"""
    assert app.file_label.value == "ファイルが選択されていません"
    assert app.run_button.disabled is True
    assert app.save_button.disabled is True
    assert not app.filepaths

def test_on_open_result_with_files(app, mock_page):
    """ファイルが選択された場合のon_open_resultの動作をテストする"""
    # ファイル選択イベントのモックを作成
    mock_file = MagicMock()
    mock_file.path = "/path/to/image.png"
    mock_event = MagicMock()
    mock_event.files = [mock_file]

    # メソッドを呼び出し
    app.on_open_result(mock_event)

    # アサーション
    assert len(app.filepaths) == 1
    assert app.filepaths[0] == "/path/to/image.png"
    assert app.file_label.value == "1個のファイルを選択中"
    assert app.run_button.disabled is False
    assert app.save_button.disabled is True
    mock_page.update.assert_called()

def test_on_open_result_no_files(app, mock_page):
    """ファイルが選択されなかった場合のon_open_resultの動作をテストする"""
    # ファイル選択イベントのモック（ファイルなし）
    mock_event = MagicMock()
    mock_event.files = None

    # メソッドを呼び出し
    app.on_open_result(mock_event)

    # アサーション
    assert not app.filepaths
    assert app.file_label.value == "ファイルが選択されていません"
    assert app.run_button.disabled is True
    mock_page.update.assert_called()

@patch('flet_ocr_app.pytesseract.image_to_string')
@patch('flet_ocr_app.Image.open')
def test_ocr_worker_success(mock_image_open, mock_image_to_string, app, mock_page):
    """OCR処理が成功するケースをテストする"""
    # モックの設定
    mock_image_to_string.return_value = "成功テキスト"
    app.filepaths = ["/fake/path/image1.png"]

    # ワーカーを実行
    app.ocr_worker()

    # アサーション
    assert "--- [1/1] image1.png の文字起こし結果 ---" in app.text_area.value
    assert "成功テキスト" in app.text_area.value
    assert "--- 全ての処理が完了しました ---" in app.text_area.value
    assert app.run_button.disabled is False
    assert app.save_button.disabled is False
    assert mock_page.update.call_count > 1 # 複数回呼ばれるはず

@patch('flet_ocr_app.pytesseract.image_to_string', side_effect=Exception("OCR Error"))
@patch('flet_ocr_app.Image.open')
def test_ocr_worker_error(mock_image_open, mock_image_to_string, app, mock_page):
    """OCR処理でエラーが発生するケースをテストする"""
    app.filepaths = ["/fake/path/image1.png"]

    # ワーカーを実行
    app.ocr_worker()

    # アサーション
    assert "処理中にエラーが発生しました: OCR Error" in app.text_area.value
    assert app.run_button.disabled is False
    assert app.save_button.disabled is False # エラーでも保存は有効になるべき

def test_save_text_with_content(app, mock_page):
    """テキストがある場合に保存処理をテストする"""
    app.text_area.value = "保存するテキスト"
    
    # 保存処理を呼び出し
    app.save_text(None)

    # アサーション
    app.save_file_picker.save_file.assert_called_with(
        dialog_title="テキストを保存",
        file_name="transcription.txt",
        allowed_extensions=["txt"],
    )

def test_save_text_no_content(app, mock_page):
    """テキストがない場合に保存処理をテストする"""
    app.text_area.value = "  "
    
    # 保存処理を呼び出し
    app.save_text(None)

    # アサーション
    assert mock_page.snack_bar.content.value == "保存するテキストがありません。"
    assert mock_page.snack_bar.open is True
    mock_page.update.assert_called()
