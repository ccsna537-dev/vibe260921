"""코스피200 지수 뷰어 (PyQt6).

kospi200_crawler.py 의 수집 함수(get_realtime / get_daily / save)를 그대로 사용하고,
현재 지수, 종가 추이 차트, 일별 시세 표를 한 화면에 보여줍니다.
데이터 수집은 별도 스레드에서 실행되므로 화면이 멈추지 않습니다.

필요 패키지: pip install PyQt6 requests openpyxl
실행: python kospi200_app.py
"""

import sys

import requests
from PyQt6.QtCore import QPointF, QRectF, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QDesktopServices, QFont, QLinearGradient, QPainter, QPainterPath,
    QPalette, QPen,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

import kospi200_crawler as crawler

# 한국 증시 관례: 상승 = 빨강, 하락 = 파랑
UP, DOWN, FLAT = QColor("#e5322d"), QColor("#1e63d6"), QColor("#8a8a8a")
AUTO_REFRESH_MS = 60_000
STOCK_COUNT = 200
STOCK_HEADERS = ["순위", "종목코드", "종목명", "현재가", "전일비", "등락률", "거래량", "거래대금", "시가총액"]


def sign_color(value):
    return UP if value > 0 else DOWN if value < 0 else FLAT


def arrow(value):
    return "▲" if value > 0 else "▼" if value < 0 else "－"


def format_value(value, suffix=""):
    return "-" if value is None else f"{value:,.2f}{suffix}"


def format_volume(value):
    return "-" if value is None else f"{value / 1000:,.0f}천주"


def format_amount(value):
    if value is None:
        return "-"
    return f"{value / 1e12:,.2f}조원" if value >= 1e12 else f"{value / 1e8:,.0f}억원"


class NumericItem(QTableWidgetItem):
    """화면에는 서식이 적용된 글자를 보이되, 정렬은 숫자 값으로 하는 표 항목."""

    def __init__(self, text, value):
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, value)

    def __lt__(self, other):
        return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)


class FetchThread(QThread):
    """현재 지수, 일별 시세, 시가총액 상위 종목을 백그라운드에서 가져온다."""

    done = pyqtSignal(dict, list, list)
    progress = pyqtSignal(int, int)   # (페이지, 지금까지 모은 종목 수)
    failed = pyqtSignal(str)

    def __init__(self, days, stock_count):
        super().__init__()
        self.days = days
        self.stock_count = stock_count

    def run(self):
        try:
            session = requests.Session()
            realtime = crawler.get_realtime(session)
            daily = crawler.get_daily(session, self.days)
            stocks = crawler.get_top_stocks(
                session, self.stock_count, progress=self.progress.emit)
            self.done.emit(realtime, daily, stocks)
        except Exception as exc:  # 네트워크/형식 오류를 화면에 알리기 위해 모두 잡는다
            self.failed.emit(str(exc))


class LineChart(QWidget):
    """종가 추이 꺾은선 차트. 마우스를 올리면 해당 날짜의 값을 보여준다."""

    MARGIN = (64, 16, 14, 26)  # 왼쪽, 오른쪽, 위, 아래

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(220)
        self.setMouseTracking(True)
        self.rows = []  # 오래된 날짜 → 최신 날짜 순
        self.hover = None

    def set_data(self, daily):
        self.rows = list(reversed(daily))
        self.hover = None
        self.update()

    def _plot_rect(self):
        left, right, top, bottom = self.MARGIN
        return QRectF(left, top, self.width() - left - right, self.height() - top - bottom)

    def _x(self, i, plot):
        n = len(self.rows)
        return plot.center().x() if n < 2 else plot.left() + plot.width() * i / (n - 1)

    def mouseMoveEvent(self, event):
        if len(self.rows) < 2:
            return
        plot = self._plot_rect()
        ratio = (event.position().x() - plot.left()) / plot.width()
        self.hover = min(max(round(ratio * (len(self.rows) - 1)), 0), len(self.rows) - 1)
        self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        text_color = self.palette().color(QPalette.ColorRole.WindowText)
        muted = QColor(text_color)
        muted.setAlpha(120)
        grid = QColor(text_color)
        grid.setAlpha(30)

        if not self.rows:
            p.setPen(muted)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "데이터가 없습니다")
            return

        plot = self._plot_rect()
        closes = [r["종가"] for r in self.rows]
        low, high = min(closes), max(closes)
        pad = (high - low) * 0.1 or 1
        low, high = low - pad, high + pad

        def y_of(v):
            return plot.bottom() - (v - low) / (high - low) * plot.height()

        # 가로 눈금선 + 값 라벨
        small = QFont(self.font())
        small.setPointSize(8)
        p.setFont(small)
        for k in range(5):
            v = low + (high - low) * k / 4
            y = y_of(v)
            p.setPen(QPen(grid, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(muted)
            p.drawText(QRectF(0, y - 8, plot.left() - 6, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{v:,.0f}")

        # 날짜 라벨 (처음 / 가운데 / 마지막)
        n = len(self.rows)
        for i in sorted({0, n // 2, n - 1}):
            x = self._x(i, plot)
            align = (Qt.AlignmentFlag.AlignLeft if i == 0 else
                     Qt.AlignmentFlag.AlignRight if i == n - 1 else Qt.AlignmentFlag.AlignHCenter)
            box = QRectF(x - 40 if align != Qt.AlignmentFlag.AlignLeft else x, plot.bottom() + 6, 80, 16)
            if align == Qt.AlignmentFlag.AlignRight:
                box.moveRight(x)
            p.setPen(muted)
            p.drawText(box, align, self.rows[i]["날짜"])

        # 선 + 아래 채우기 (기간 전체가 올랐으면 빨강, 내렸으면 파랑)
        color = sign_color(closes[-1] - closes[0])
        points = [QPointF(self._x(i, plot), y_of(c)) for i, c in enumerate(closes)]
        line = QPainterPath(points[0])
        for pt in points[1:]:
            line.lineTo(pt)
        area = QPainterPath(line)
        area.lineTo(points[-1].x(), plot.bottom())
        area.lineTo(points[0].x(), plot.bottom())
        area.closeSubpath()
        gradient = QLinearGradient(0, plot.top(), 0, plot.bottom())
        top_color = QColor(color)
        top_color.setAlpha(70)
        bottom_color = QColor(color)
        bottom_color.setAlpha(0)
        gradient.setColorAt(0, top_color)
        gradient.setColorAt(1, bottom_color)
        p.fillPath(area, QBrush(gradient))
        p.setPen(QPen(color, 2))
        p.drawPath(line)

        # 마우스가 가리키는 지점
        if self.hover is not None:
            pt = points[self.hover]
            row = self.rows[self.hover]
            p.setPen(QPen(muted, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(pt.x(), plot.top()), QPointF(pt.x(), plot.bottom()))
            p.setBrush(color)
            p.setPen(QPen(self.palette().color(QPalette.ColorRole.Base), 2))
            p.drawEllipse(pt, 5, 5)

            lines = [row["날짜"],
                     f"종가 {row['종가']:,.2f}",
                     f"{arrow(row['전일비'])} {abs(row['전일비']):,.2f} ({row['등락률(%)']:+.2f}%)"]
            metrics = p.fontMetrics()
            w = max(metrics.horizontalAdvance(t) for t in lines) + 16
            h = metrics.height() * len(lines) + 12
            bx = pt.x() + 12 if pt.x() + 12 + w < self.width() else pt.x() - 12 - w
            by = min(max(pt.y() - h / 2, plot.top()), plot.bottom() - h)
            p.setPen(QPen(muted, 1))
            p.setBrush(self.palette().color(QPalette.ColorRole.Base))
            p.drawRoundedRect(QRectF(bx, by, w, h), 6, 6)
            for k, t in enumerate(lines):
                p.setPen(sign_color(row["전일비"]) if k == 2 else text_color)
                p.drawText(QRectF(bx + 8, by + 6 + k * metrics.height(), w, metrics.height()),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, t)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("코스피200 지수 뷰어")
        self.resize(980, 760)

        self.realtime = None
        self.daily = []
        self.stocks = []
        self.thread = None

        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        QTimer.singleShot(0, self.refresh)

    # ---------- UI ----------
    def _build_ui(self):
        # 현재 지수
        self.name_label = QLabel("코스피 200")
        self.name_label.setStyleSheet("color: gray; font-size: 11pt;")
        self.price_label = QLabel("-")
        price_font = QFont()
        price_font.setPointSize(30)
        price_font.setBold(True)
        self.price_label.setFont(price_font)
        self.change_label = QLabel("")
        change_font = QFont()
        change_font.setPointSize(13)
        change_font.setBold(True)
        self.change_label.setFont(change_font)
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: gray;")

        head_left = QVBoxLayout()
        head_left.setSpacing(0)
        for w in (self.name_label, self.price_label, self.change_label, self.time_label):
            head_left.addWidget(w)

        self.stat_labels = {}
        stats = QHBoxLayout()
        for key in ("시가", "고가", "저가", "거래량", "거래대금"):
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stat_labels[key] = label
            self._set_stat(key, "-")
            stats.addWidget(label)

        head = QHBoxLayout()
        head.addLayout(head_left)
        head.addStretch(1)
        head.addLayout(stats)
        head.setSpacing(24)

        # 조작 줄
        self.days_spin = QSpinBox()
        self.days_spin.setRange(5, 250)
        self.days_spin.setValue(30)
        self.days_spin.setSuffix(" 거래일")
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.clicked.connect(self.refresh)
        self.auto_check = QCheckBox("1분마다 자동 새로고침")
        self.auto_check.toggled.connect(self._toggle_auto)
        self.save_btn = QPushButton("저장 (Excel/CSV/JSON)")
        self.save_btn.clicked.connect(self.save_data)
        self.save_btn.setEnabled(False)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("조회 기간"))
        controls.addWidget(self.days_spin)
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.auto_check)
        controls.addStretch(1)
        controls.addWidget(self.save_btn)

        # 차트 + 표
        self.chart = LineChart()

        self.table = QTableWidget(0, len(crawler.DAILY_FIELDS))
        self.table.setHorizontalHeaderLabels(crawler.DAILY_FIELDS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.chart)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        # 시가총액 상위 종목 탭
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("종목명 또는 종목코드로 검색")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_stock_filter)
        self.stock_count_label = QLabel("")
        self.stock_count_label.setStyleSheet("color: gray;")

        stock_top = QHBoxLayout()
        stock_top.addWidget(self.filter_edit, 1)
        stock_top.addWidget(self.stock_count_label)

        self.stock_table = QTableWidget(0, len(STOCK_HEADERS))
        self.stock_table.setHorizontalHeaderLabels(STOCK_HEADERS)
        self.stock_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stock_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.stock_table.verticalHeader().setVisible(False)
        self.stock_table.setAlternatingRowColors(True)
        self.stock_table.setSortingEnabled(True)  # 머리글을 누르면 숫자 기준으로 정렬
        self.stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stock_table.cellDoubleClicked.connect(self._open_stock_page)
        hint = QLabel("머리글을 클릭하면 정렬, 행을 더블클릭하면 네이버 증권 종목 페이지가 열립니다.")
        hint.setStyleSheet("color: gray;")

        stock_tab = QWidget()
        stock_layout = QVBoxLayout(stock_tab)
        stock_layout.setContentsMargins(0, 6, 0, 0)
        stock_layout.addLayout(stock_top)
        stock_layout.addWidget(self.stock_table, 1)
        stock_layout.addWidget(hint)

        self.tabs = QTabWidget()
        self.tabs.addTab(splitter, "지수 추이 · 일별 시세")
        self.tabs.addTab(stock_tab, f"시가총액 상위 {STOCK_COUNT} 종목")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(head)
        layout.addLayout(controls)
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("데이터를 불러오는 중…")

    def _set_stat(self, key, value):
        self.stat_labels[key].setText(
            f"<span style='color:gray;font-size:9pt'>{key}</span><br><b style='font-size:12pt'>{value}</b>")

    def _toggle_auto(self, on):
        if on:
            self.timer.start(AUTO_REFRESH_MS)
        else:
            self.timer.stop()

    # ---------- 데이터 ----------
    def refresh(self):
        if self.thread and self.thread.isRunning():
            return
        self.refresh_btn.setEnabled(False)
        self.statusBar().showMessage("불러오는 중…")
        self.thread = FetchThread(self.days_spin.value(), STOCK_COUNT)
        self.thread.done.connect(self.on_done)
        self.thread.progress.connect(
            lambda page, n: self.statusBar().showMessage(
                f"종목 수집 중… {page}페이지 ({n}/{STOCK_COUNT}개)"))
        self.thread.failed.connect(self.on_failed)
        self.thread.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self.thread.start()

    def on_done(self, realtime, daily, stocks):
        self.realtime, self.daily, self.stocks = realtime, daily, stocks
        self.save_btn.setEnabled(True)

        change = realtime["전일비"]
        color = sign_color(change).name()
        self.name_label.setText(realtime["지수명"])
        self.price_label.setText(f"{realtime['현재가']:,.2f}")
        self.price_label.setStyleSheet(f"color: {color};")
        self.change_label.setText(
            f"{arrow(change)} {abs(change):,.2f}  ({realtime['등락률(%)']:+.2f}%)")
        self.change_label.setStyleSheet(f"color: {color};")
        state = "장중" if realtime["장상태"] == "OPEN" else "장 마감"
        self.time_label.setText(f"{state} · {realtime['기준시각'][:16].replace('T', ' ')}")

        self._set_stat("시가", format_value(realtime["시가"]))
        self._set_stat("고가", format_value(realtime["고가"]))
        self._set_stat("저가", format_value(realtime["저가"]))
        self._set_stat("거래량", format_volume(realtime["거래량(주)"]))
        self._set_stat("거래대금", format_amount(realtime["거래대금(원)"]))

        self.chart.set_data(daily)
        self._fill_table(daily)
        self._fill_stock_table(stocks)
        self.statusBar().showMessage(
            f"불러오기 완료 · 일별 시세 {len(daily)}건 · 종목 {len(stocks)}개", 5000)

    def on_failed(self, message):
        self.statusBar().showMessage("불러오기에 실패했습니다.")
        QMessageBox.warning(
            self, "불러오기 실패",
            f"{message}\n\n인터넷 연결을 확인하세요. 네이버 API 주소나 형식이 바뀌었을 수도 있습니다.")

    def _fill_table(self, daily):
        self.table.setRowCount(len(daily))
        for row, item in enumerate(daily):
            cells = [
                (item["날짜"], None),
                (format_value(item["종가"]), None),
                (f"{arrow(item['전일비'])} {abs(item['전일비']):,.2f}", sign_color(item["전일비"])),
                (f"{item['등락률(%)']:+.2f}%", sign_color(item["등락률(%)"])),
                (format_value(item["시가"]), None),
                (format_value(item["고가"]), None),
                (format_value(item["저가"]), None),
            ]
            for col, (text, color) in enumerate(cells):
                cell = QTableWidgetItem(text)
                cell.setTextAlignment(
                    (Qt.AlignmentFlag.AlignCenter if col == 0 else Qt.AlignmentFlag.AlignRight)
                    | Qt.AlignmentFlag.AlignVCenter)
                if color:
                    cell.setForeground(color)
                self.table.setItem(row, col, cell)

    def _fill_stock_table(self, stocks):
        table = self.stock_table
        table.setSortingEnabled(False)  # 채우는 동안 정렬이 끼어들면 행이 뒤섞이므로 잠시 끔
        table.setRowCount(len(stocks))
        for row, s in enumerate(stocks):
            cells = [
                (str(s["순위"]), s["순위"], None, Qt.AlignmentFlag.AlignCenter),
                (s["종목코드"], s["종목코드"], None, Qt.AlignmentFlag.AlignCenter),
                (s["종목명"], s["종목명"], None, Qt.AlignmentFlag.AlignLeft),
                (f"{s['현재가']:,.0f}", s["현재가"], None, Qt.AlignmentFlag.AlignRight),
                (f"{arrow(s['전일비'])} {abs(s['전일비']):,.0f}", s["전일비"],
                 sign_color(s["전일비"]), Qt.AlignmentFlag.AlignRight),
                (f"{s['등락률(%)']:+.2f}%", s["등락률(%)"],
                 sign_color(s["등락률(%)"]), Qt.AlignmentFlag.AlignRight),
                (f"{s['거래량(주)']:,.0f}", s["거래량(주)"], None, Qt.AlignmentFlag.AlignRight),
                (format_amount(s["거래대금(원)"]), s["거래대금(원)"], None, Qt.AlignmentFlag.AlignRight),
                (format_amount(s["시가총액(원)"]), s["시가총액(원)"], None, Qt.AlignmentFlag.AlignRight),
            ]
            for col, (text, value, color, align) in enumerate(cells):
                item = NumericItem(text, value)
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if color:
                    item.setForeground(color)
                table.setItem(row, col, item)
        table.setSortingEnabled(True)
        table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._apply_stock_filter(self.filter_edit.text())

    def _apply_stock_filter(self, text):
        keyword = text.strip().lower()
        shown = 0
        for row in range(self.stock_table.rowCount()):
            code = self.stock_table.item(row, 1).text().lower()
            name = self.stock_table.item(row, 2).text().lower()
            match = not keyword or keyword in code or keyword in name
            self.stock_table.setRowHidden(row, not match)
            shown += match
        total = self.stock_table.rowCount()
        self.stock_count_label.setText(f"{shown} / {total}개" if keyword else f"{total}개")

    def _open_stock_page(self, row, _column):
        code = self.stock_table.item(row, 1).text()
        QDesktopServices.openUrl(QUrl(f"https://stock.naver.com/domestic/stock/{code}"))

    # ---------- 저장 ----------
    def save_data(self):
        if not self.realtime:
            return
        path, selected = QFileDialog.getSaveFileName(
            self, "저장", "kospi200.xlsx",
            "Excel 파일 (*.xlsx);;CSV 파일 (*.csv);;JSON 파일 (*.json)")
        if not path:
            return
        if not path.lower().endswith((".xlsx", ".csv", ".json")):
            path += ".csv" if "CSV" in selected else ".json" if "JSON" in selected else ".xlsx"
        try:
            crawler.save(self.realtime, self.daily, path, self.stocks)
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
        self.timer.stop()
        if self.thread and self.thread.isRunning():
            self.thread.wait(5000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
