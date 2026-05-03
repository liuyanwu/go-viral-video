"""Tests for downloader module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from modules.downloader import VideoDownloader
from models import Platform, VideoInfo
from exceptions import DownloadError

def test_downloader_initialization():
    d = VideoDownloader()
    assert d.output_dir.exists()

def test_local_file_validation(tmp_path):
    d = VideoDownloader()
    test_file = tmp_path / "test.mp4"
    test_file.touch()
    info = d.download(str(test_file))
    assert info.platform == Platform.LOCAL
    assert info.local_path == str(test_file.resolve())

def test_local_file_not_found():
    d = VideoDownloader()
    with pytest.raises(DownloadError):
        d.download("https://example.com/nonexistent.mp4")

def test_local_unsupported_format(tmp_path):
    d = VideoDownloader()
    test_file = tmp_path / "test.txt"
    test_file.touch()
    with pytest.raises(ValueError):
        d.download(str(test_file))
