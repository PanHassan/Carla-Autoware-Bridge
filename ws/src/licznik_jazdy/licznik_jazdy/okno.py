import signal
import sys
import threading

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
import rclpy
from rclpy.executors import SingleThreadedExecutor, ExternalShutdownException
from licznik_jazdy.licznik import Licznik, NAZWY_TRYBOW, tekst


class Okno(QWidget):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.setWindowTitle('Licznik jazdy')
        self.setStyleSheet('font-size: 20px')
        self.predkosc = QLabel()
        self.predkosc.setStyleSheet('font-size: 64px; font-weight: bold')
        self.tryb = QLabel()
        self.dystans = QLabel()
        self.maksymalna = QLabel()
        self.autonomicznie = QLabel()
        uklad = QVBoxLayout(self)
        for label in (self.predkosc, self.tryb, self.dystans,
                      self.maksymalna, self.autonomicznie):
            uklad.addWidget(label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.odswiez)
        self.timer.start(100)
        self.odswiez()

    def odswiez(self):
        s = self.node.snapshot()
        self.predkosc.setText(f'{tekst(s.predkosc_kmh, "{:.0f}")} km/h')
        self.tryb.setText(f'Tryb: {NAZWY_TRYBOW.get(s.tryb, "—")}')
        self.dystans.setText(f'Dystans: {s.dystans_m:.0f} m')
        self.maksymalna.setText(f'Maksymalna prędkość: {s.max_predkosc_kmh:.1f} km/h')
        self.autonomicznie.setText(
            f'Jazda autonomiczna: {s.czas_autonomiczny_s:.0f} s')


def main(args=None):
    rclpy.init(args=args)
    app = QApplication(sys.argv[:1])
    node = Licznik('licznik_jazdy_okno')
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    def spin():
        try:
            executor.spin()
        except ExternalShutdownException:
            pass

    watek = threading.Thread(target=spin)
    okno = Okno(node)
    poprzedni_handler = signal.signal(signal.SIGINT, lambda *_: app.quit())
    watek.start()
    try:
        okno.show()
        app.exec_()
    finally:
        okno.timer.stop()
        executor.shutdown()
        watek.join()
        node.destroy_node()
        rclpy.try_shutdown()
        signal.signal(signal.SIGINT, poprzedni_handler)
