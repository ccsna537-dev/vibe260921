"""네이버 뉴스 크롤러 GUI 앱 (PyQt6).

naver_news_crawler.py 의 크롤링 함수(fetch / parse_search / extract_body / save)를 그대로 사용하고,
그 위에 PyQt6 화면을 얹은 프로그램입니다. 크롤링은 별도 스레드에서 실행되므로 화면이 멈추지 않습니다.

필요 패키지: pip install PyQt6 requests beautifulsoup4 openpyxl
실행: python naver_news_app.py
"""

import sys
from urllib.parse import quote

import requests
from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QDoubleSpinBox, QFileDialog,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import naver_news_crawler as crawler

SEARCH_URL = "https://search.naver.com/search.naver?where=nexearch&ie=utf8&query={}"

# 표 열 번호
COL_NO, COL_PRESS, COL_TITLE, COL_TIME, COL_STATE = range(5)


class CrawlThread(QThread):
    """검색 결과 수집 → (선택) 기사별 본문 수집을 백그라운드에서 수행한다."""

    listReady = pyqtSignal(list)         # 기사 목록
    bodyReady = pyqtSignal(int, str)     # (기사 번호, 본문)
    progress = pyqtSignal(int, int)      # (완료 수, 전체 수)
    failed = pyqtSignal(str)

    def __init__(self, url, limit, fetch_body, delay):
        super().__init__()
        self.url = url
        self.limit = limit
        self.fetch_body = fetch_body
        self.delay = delay

    def run(self):
        session = requests.Session()
        html = crawler.fetch(session, self.url)
        if not html:
            self.failed.emit("검색 결과 페이지를 가져오지 못했습니다. 인터넷 연결을 확인하세요.")
            return

        articles = crawler.parse_search(html)[: self.limit]
        urls = [a["url"] for a in articles]  # emit 이후에는 메인 스레드가 목록을 소유
        self.listReady.emit(articles)
        if not articles or not self.fetch_body:
            return

        for i, url in enumerate(urls):
            # 요청 간 대기 (중지 요청에 바로 반응하도록 잘게 쪼갬)
            for _ in range(int(self.delay * 10)):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)
            if self.isInterruptionRequested():
                return

            page = crawler.fetch(session, url)
            self.bodyReady.emit(i, crawler.extract_body(page) if page else "")
            self.progress.emit(i + 1, len(urls))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1150, 720)

        self.articles = []
        self.thread = None
        self.fetch_body = True

        self._build_ui()
        self._set_running(False)

    # ---------- UI 구성 ----------
    def _build_ui(self):
        # 상단: 검색 옵션
        self.keyword = QLineEdit("동물용의약품")
        self.keyword.setPlaceholderText("검색어를 입력하세요")
        self.keyword.returnPressed.connect(self.start_search)

        self.limit = QSpinBox()
        self.limit.setRange(1, 30)
        self.limit.setValue(10)

        self.body_check = QCheckBox("본문 가져오기")
        self.body_check.setChecked(True)
        self.body_check.toggled.connect(lambda on: self.delay.setEnabled(on))

        self.delay = QDoubleSpinBox()
        self.delay.setRange(0.5, 10.0)
        self.delay.setSingleStep(0.5)
        self.delay.setValue(1.0)
        self.delay.setSuffix(" 초")

        self.search_btn = QPushButton("검색")
        self.search_btn.setDefault(True)
        self.search_btn.clicked.connect(self.start_search)
        self.stop_btn = QPushButton("중지")
        self.stop_btn.clicked.connect(self.stop_search)

        top = QHBoxLayout()
        top.addWidget(QLabel("검색어"))
        top.addWidget(self.keyword, 1)
        top.addWidget(QLabel("기사 수"))
        top.addWidget(self.limit)
        top.addWidget(self.body_check)
        top.addWidget(QLabel("요청 간격"))
        top.addWidget(self.delay)
        top.addWidget(self.search_btn)
        top.addWidget(self.stop_btn)

        # 좌측: 기사 목록 표
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "언론사", "제목", "시간", "본문"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_NO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_PRESS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_TIME, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_STATE, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.show_detail)

        # 우측: 기사 상세
        self.title_label = QLabel("기사를 선택하세요")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setWordWrap(True)
        self.title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color: gray;")

        self.body_view = QPlainTextEdit()
        self.body_view.setReadOnly(True)
        body_font = QFont()
        body_font.setPointSize(11)
        self.body_view.setFont(body_font)

        self.open_btn = QPushButton("브라우저에서 열기")
        self.open_btn.clicked.connect(self.open_in_browser)
        self.copy_btn = QPushButton("본문 복사")
        self.copy_btn.clicked.connect(self.copy_body)
        self.save_btn = QPushButton("전체 저장 (Excel/JSON/CSV)")
        self.save_btn.clicked.connect(self.save_all)

        buttons = QHBoxLayout()
        buttons.addWidget(self.open_btn)
        buttons.addWidget(self.copy_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.save_btn)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(8, 0, 0, 0)
        detail_layout.addWidget(self.title_label)
        detail_layout.addWidget(self.meta_label)
        detail_layout.addWidget(self.body_view, 1)
        detail_layout.addLayout(buttons)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        # 하단 상태바
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(220)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().showMessage("검색어를 입력하고 [검색]을 누르세요.")

    def _set_running(self, running):
        for w in (self.keyword, self.limit, self.body_check, self.search_btn):
            w.setEnabled(not running)
        self.delay.setEnabled(not running and self.body_check.isChecked())
        self.stop_btn.setEnabled(running)
        self.save_btn.setEnabled(not running and bool(self.articles))

    # ---------- 검색 ----------
    def start_search(self):
        keyword = self.keyword.text().strip()
        if not keyword:
            QMessageBox.warning(self, "검색어 없음", "검색어를 입력하세요.")
            return

        self.articles = []
        self.table.setRowCount(0)
        self._clear_detail()
        self.fetch_body = self.body_check.isChecked()
        self._set_running(True)
        self.progress_bar.setRange(0, 0)  # 목록 수집 중에는 진행 표시줄을 '진행 중' 애니메이션으로
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage(f"'{keyword}' 검색 중…")

        self.thread = CrawlThread(
            SEARCH_URL.format(quote(keyword)),
            self.limit.value(),
            self.fetch_body,
            self.delay.value(),
        )
        self.thread.listReady.connect(self.on_list_ready)
        self.thread.bodyReady.connect(self.on_body_ready)
        self.thread.progress.connect(self.on_progress)
        self.thread.failed.connect(self.on_failed)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def stop_search(self):
        if self.thread and self.thread.isRunning():
            self.thread.requestInterruption()
            self.stop_btn.setEnabled(False)
            self.statusBar().showMessage("중지하는 중…")

    def on_list_ready(self, articles):
        self.articles = articles
        if not articles:
            QMessageBox.information(
                self, "결과 없음",
                "기사를 찾지 못했습니다.\n검색어를 바꾸거나, 네이버 페이지 구조가 바뀌었는지 확인하세요.")
            return

        self.table.setRowCount(len(articles))
        for row, art in enumerate(articles):
            values = [str(row + 1), art["press"], art["title"], art["posted"],
                      "대기" if self.fetch_body else "-"]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col in (COL_NO, COL_STATE):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
        self.table.selectRow(0)

        if self.fetch_body:
            self.progress_bar.setRange(0, len(articles))
            self.progress_bar.setValue(0)
            self.statusBar().showMessage(f"기사 {len(articles)}건 발견 · 본문을 가져오는 중…")
        else:
            self.statusBar().showMessage(f"기사 {len(articles)}건 발견")

    def on_body_ready(self, index, body):
        self.articles[index]["body"] = body
        state = "완료" if body else "실패"
        self.table.item(index, COL_STATE).setText(state)
        if self.table.currentRow() == index:
            self.show_detail()

    def on_progress(self, done, total):
        self.progress_bar.setValue(done)
        self.statusBar().showMessage(f"본문 수집 중… {done}/{total}")

    def on_failed(self, message):
        QMessageBox.critical(self, "오류", message)
        self.statusBar().showMessage("오류가 발생했습니다.")

    def on_finished(self):
        interrupted = self.thread.isInterruptionRequested()
        self.progress_bar.setVisible(False)
        self._set_running(False)
        if self.articles:
            done = sum(1 for a in self.articles if a["body"])
            suffix = "중지됨" if interrupted else "완료"
            if self.fetch_body:
                self.statusBar().showMessage(
                    f"{suffix}: 기사 {len(self.articles)}건 중 본문 {done}건 수집")
            else:
                self.statusBar().showMessage(f"{suffix}: 기사 {len(self.articles)}건")

    # ---------- 상세 보기 / 동작 ----------
    def _current_article(self):
        row = self.table.currentRow()
        return self.articles[row] if 0 <= row < len(self.articles) else None

    def _clear_detail(self):
        self.title_label.setText("기사를 선택하세요")
        self.meta_label.setText("")
        self.body_view.clear()

    def show_detail(self):
        art = self._current_article()
        if not art:
            self._clear_detail()
            return
        self.title_label.setText(art["title"])
        self.meta_label.setText(f"{art['press']} · {art['posted']}")

        if art["body"]:
            self.body_view.setPlainText(art["body"])
        elif not self.fetch_body:
            self.body_view.setPlainText(
                (art["summary"] + "\n\n" if art["summary"] else "")
                + "('본문 가져오기'를 켜고 검색하면 기사 본문을 볼 수 있습니다.)")
        elif self.table.item(self.table.currentRow(), COL_STATE).text() == "대기":
            self.body_view.setPlainText(art["summary"] + "\n\n(본문을 가져오는 중입니다…)")
        else:
            self.body_view.setPlainText(
                (art["summary"] + "\n\n" if art["summary"] else "")
                + "(본문을 가져오지 못했습니다. 유료/로그인 기사이거나 접속이 차단되었을 수 있습니다.)")

    def open_in_browser(self):
        art = self._current_article()
        if art:
            QDesktopServices.openUrl(QUrl(art["url"]))
        else:
            self.statusBar().showMessage("먼저 기사를 선택하세요.", 3000)

    def copy_body(self):
        art = self._current_article()
        if art and art["body"]:
            QApplication.clipboard().setText(f"{art['title']}\n\n{art['body']}")
            self.statusBar().showMessage("본문을 클립보드에 복사했습니다.", 3000)
        else:
            self.statusBar().showMessage("복사할 본문이 없습니다.", 3000)

    def save_all(self):
        if not self.articles:
            return
        path, selected = QFileDialog.getSaveFileName(
            self, "저장", f"naver_news_{self.keyword.text().strip()}.xlsx",
            "Excel 파일 (*.xlsx);;JSON 파일 (*.json);;CSV 파일 (*.csv)")
        if not path:
            return
        if not path.lower().endswith((".xlsx", ".json", ".csv")):
            path += ".csv" if "CSV" in selected else ".json" if "JSON" in selected else ".xlsx"
        try:
            crawler.save(self.articles, path)
        except PermissionError:
            QMessageBox.critical(
                self, "저장 실패",
                f"파일에 쓸 수 없습니다.\n엑셀 등에서 같은 파일이 열려 있다면 닫고 다시 시도하세요.\n\n{path}")
            return
        except (OSError, RuntimeError) as exc:
            QMessageBox.critical(self, "저장 실패", str(exc))
            return
        self.statusBar().showMessage(f"저장 완료: {path}", 5000)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.requestInterruption()
            self.thread.wait(3000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
