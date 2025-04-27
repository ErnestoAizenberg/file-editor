import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, mock_open
import py_compile

from file_editor import (
    clear_screen,
    log_history,
    read_file_with_encoding,
    write_file_with_encoding,
    replace_in_file,
    delete_from_file,
    replace_in_directory,
    delete_from_directory,
    check_syntax,
    search_in_files,
)

# Fixtures for test setup
@pytest.fixture
def temp_dir():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_files(temp_dir):
    # Create sample files for testing
    files = {
        "test1.py": "print('Hello World')\n",
        "test2.py": "def foo():\n    return 'bar'\n",
        "test3.txt": "This is not a Python file\n",
        "subdir/test4.py": "import os\n\nprint(os.getcwd())\n",
    }
    
    for filename, content in files.items():
        path = os.path.join(temp_dir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return temp_dir

@pytest.fixture
def history():
    return []

# Test cases
def test_clear_screen():
    with patch('os.system') as mock_system:
        clear_screen()
        mock_system.assert_called_once()

def test_log_history(history):
    log_history("Test action", history)
    assert len(history) == 1
    assert history[0] == "Test action"
    
    log_history("Another action", history)
    assert len(history) == 2

def test_read_file_with_encoding_success():
    content = "test content"
    with patch('builtins.open', mock_open(read_data=content)):
        result = read_file_with_encoding("dummy.txt")
        assert result == content

def test_read_file_with_encoding_fallback():
    content = "test content"
    with patch('builtins.open', side_effect=[
        UnicodeDecodeError("utf-8", b"", 0, 1, "test"),
        mock_open(read_data=content).return_value
    ]):
        result = read_file_with_encoding("dummy.txt")
        assert result == content

def test_read_file_with_encoding_failure():
    with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
        result = read_file_with_encoding("nonexistent.txt")
        assert result is None

def test_write_file_with_encoding_success():
    with patch('builtins.open', mock_open()) as mock_file:
        result = write_file_with_encoding("dummy.txt", "test content")
        assert result is True
        mock_file().write.assert_called_once_with("test content")

def test_write_file_with_encoding_failure():
    with patch('builtins.open', side_effect=IOError("Permission denied")):
        result = write_file_with_encoding("dummy.txt", "test content")
        assert result is False

def test_replace_in_file_success(sample_files):
    file_path = os.path.join(sample_files, "test1.py")
    result = replace_in_file(file_path, "Hello", "Hi")
    assert result is True
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert "Hi World" in content

def test_replace_in_file_no_change(sample_files):
    file_path = os.path.join(sample_files, "test1.py")
    result = replace_in_file(file_path, "Nonexistent", "New")
    assert result is False

def test_replace_in_file_failure(sample_files):
    result = replace_in_file(os.path.join(sample_files, "nonexistent.py"), "a", "b")
    assert result is False

def test_delete_from_file_success(sample_files):
    file_path = os.path.join(sample_files, "test1.py")
    result = delete_from_file(file_path, "Hello")
    assert result is True
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert "Hello" not in content
    assert "World" in content

def test_delete_from_file_no_change(sample_files):
    file_path = os.path.join(sample_files, "test1.py")
    result = delete_from_file(file_path, "Nonexistent")
    assert result is False

def test_replace_in_directory(sample_files, history):
    changes = replace_in_directory(sample_files, "print", "PRINT", history)
    assert len(changes) == 2  # test1.py and subdir/test4.py
    assert os.path.join(sample_files, "test1.py") in changes
    assert os.path.join(sample_files, "subdir/test4.py") in changes
    
    # Verify changes were made
    with open(os.path.join(sample_files, "test1.py"), 'r', encoding='utf-8') as f:
        assert "PRINT" in f.read()

def test_delete_from_directory(sample_files, history):
    changes = delete_from_directory(sample_files, "print", history)
    assert len(changes) == 2  # test1.py and subdir/test4.py
    assert os.path.join(sample_files, "test1.py") in changes
    assert os.path.join(sample_files, "subdir/test4.py") in changes
    
    # Verify changes were made
    with open(os.path.join(sample_files, "test1.py"), 'r', encoding='utf-8') as f:
        assert "print" not in f.read()

def test_check_syntax_success(sample_files):
    errors = check_syntax(sample_files)
    assert len(errors) == 0

def test_check_syntax_error(sample_files):
    # Create a file with syntax error
    bad_file = os.path.join(sample_files, "bad.py")
    with open(bad_file, 'w', encoding='utf-8') as f:
        f.write("print('Hello' # Missing closing parenthesis\n")
    
    errors = check_syntax(sample_files)
    assert len(errors) == 1
    assert "bad.py" in errors[0]

def test_search_in_files(sample_files):
    results = search_in_files(sample_files, "print")
    assert len(results) == 2  # test1.py and subdir/test4.py
    assert os.path.join(sample_files, "test1.py") in results
    assert os.path.join(sample_files, "subdir/test4.py") in results

def test_search_in_files_not_found(sample_files):
    results = search_in_files(sample_files, "nonexistent_pattern")
    assert len(results) == 0

# Integration tests for the main function
def test_main_replace_command(sample_files, history):
    with patch('builtins.input', side_effect=[
        sample_files,  # directory input
        "replace Hello Hi",  # command
        "y",  # confirmation
        "exit"  # exit command
    ]), patch('file_editor.continue_prompt'):
        from file_editor import main
        main()
    
    # Verify changes were made
    with open(os.path.join(sample_files, "test1.py"), 'r', encoding='utf-8') as f:
        assert "Hi World" in f.read()

def test_main_delete_command(sample_files, history):
    with patch('builtins.input', side_effect=[
        sample_files,  # directory input
        "delete print",  # command
        "y",  # confirmation
        "exit"  # exit command
    ]), patch('file_editor.continue_prompt'):
        from file_editor import main
        main()
    
    # Verify changes were made
    with open(os.path.join(sample_files, "test1.py"), 'r', encoding='utf-8') as f:
        assert "print" not in f.read()

def test_main_check_command(sample_files, capsys):
    with patch('builtins.input', side_effect=[
        sample_files,  # directory input
        "check",  # command
        "exit"  # exit command
    ]), patch('file_editor.continue_prompt'):
        from file_editor import main
        main()
    
    captured = capsys.readouterr()
    assert "Ошибок синтаксиса не найдено" in captured.out

def test_main_search_command(sample_files, capsys):
    with patch('builtins.input', side_effect=[
        sample_files,  # directory input
        "search print",  # command
        "exit"  # exit command
    ]), patch('file_editor.continue_prompt'):
        from file_editor import main
        main()
    
    captured = capsys.readouterr()
    assert "test1.py" in captured.out
    assert "subdir/test4.py" in captured.out

def test_main_history_command(sample_files, capsys, history):
    with patch('builtins.input', side_effect=[
        sample_files,  # directory input
        "search print",  # command
        "history",  # command
        "exit"  # exit command
    ]), patch('file_editor.continue_prompt'):
        from file_editor import main
        main()
    
    captured = capsys.readouterr()
    assert "История изменений" in captured.out
    assert "Поиск строки 'print' завершен" in captured.out

def test_main_help_command(capsys):
    with patch('builtins.input', side_effect=[
        "dummy_dir",  # directory input
        "help",  # command
        "exit"  # exit command
    ]), patch('file_editor.continue_prompt'):
        from file_editor import main
        main()
    
    captured = capsys.readouterr()
    assert "Доступные команды" in captured.out
