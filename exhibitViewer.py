import sys
import os
from PyQt5 import QtWidgets, QtGui, QtCore
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import io

class PDFTab(QtWidgets.QWidget):
    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.page_count = len(self.doc)
        self.current_page = 0
        self.zoom_level = 1.0  # Zoom level factor (1.0 means 100%)
        self.top_text = "Exhibit"
        self.bottom_text = "Bottom Text"  # Default bottom text
        self.sticker_mode = False

        # Create layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Create toolbar
        self.create_toolbar()

        # Create PDF viewer inside a scroll area
        self.create_pdf_viewer()

        # Load PDF
        self.load_pdf()

        # Enable gesture recognition
        self.grabGesture(QtCore.Qt.PinchGesture)

        # Install event filter to capture mouse clicks on the PDF
        self.pdf_label.installEventFilter(self)

    def create_toolbar(self):
        toolbar = QtWidgets.QToolBar()
        self.layout.addWidget(toolbar)

        btn_prev = QtWidgets.QAction('Previous Page', self)
        btn_prev.triggered.connect(self.prev_page)
        toolbar.addAction(btn_prev)

        btn_next = QtWidgets.QAction('Next Page', self)
        btn_next.triggered.connect(self.next_page)
        toolbar.addAction(btn_next)

        self.page_input = QtWidgets.QLineEdit()
        self.page_input.setValidator(QtGui.QIntValidator(1, self.page_count))  # Only allow valid page numbers
        self.page_input.setFixedWidth(50)
        self.page_input.setText(str(self.current_page + 1))  # Show current page (1-based index)
        self.page_input.returnPressed.connect(self.goto_page)  # Jump to the entered page number when Enter is pressed
        toolbar.addWidget(self.page_input)

        btn_change_top_text = QtWidgets.QAction('Change Top Text', self)
        btn_change_top_text.triggered.connect(self.change_top_text)
        toolbar.addAction(btn_change_top_text)

        btn_add_sticker = QtWidgets.QAction('Add Sticker', self)
        btn_add_sticker.triggered.connect(self.enable_sticker_mode)
        toolbar.addAction(btn_add_sticker)

        btn_delete_stickers = QtWidgets.QAction('Delete Stickers', self)
        btn_delete_stickers.triggered.connect(self.delete_stickers)
        toolbar.addAction(btn_delete_stickers)

        btn_save = QtWidgets.QAction('Save PDF', self)
        btn_save.triggered.connect(self.save_pdf)
        toolbar.addAction(btn_save)

    def create_pdf_viewer(self):
        # Create a QScrollArea to contain the QLabel
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.pdf_label = QtWidgets.QLabel()
        self.pdf_label.setAlignment(QtCore.Qt.AlignCenter)

        # Add the QLabel to the scroll area
        self.scroll_area.setWidget(self.pdf_label)
        self.scroll_area.setWidgetResizable(True)

        # Add the scroll area to the main layout
        self.layout.addWidget(self.scroll_area)

    def load_pdf(self):
        # Render the current page as an image and display it
        self.display_pdf()

    def display_pdf(self):
        # Adjust the zoom level dynamically using the zoom_level factor
        zoom = self.zoom_level * (300 / 72)  # Default DPI 72, we want 300 DPI scaling with zoom
        mat = fitz.Matrix(zoom, zoom)
        page = self.doc.load_page(self.current_page)  # PyMuPDF page object
        pix = page.get_pixmap(matrix=mat)  # Render page to an image with the adjusted DPI

        # Convert the pixmap to QImage
        image = QtGui.QImage(pix.samples, pix.width, pix.height, pix.stride, QtGui.QImage.Format_RGB888)

        # Set the QImage on the QLabel
        self.pdf_label.setPixmap(QtGui.QPixmap.fromImage(image))

        # Update the page input field to reflect the current page (1-based index)
        self.page_input.setText(str(self.current_page + 1))

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.display_pdf()

    def next_page(self):
        if self.current_page < self.page_count - 1:
            self.current_page += 1
            self.display_pdf()

    def goto_page(self):
        try:
            # Get the entered page number from QLineEdit (1-based index)
            page_number = int(self.page_input.text()) - 1  # Convert to 0-based index
            if 0 <= page_number < self.page_count:
                self.current_page = page_number
                self.display_pdf()
        except ValueError:
            pass  # Invalid input, do nothing

    def change_top_text(self):
        text, ok = QtWidgets.QInputDialog.getText(self, 'Top Text', 'Enter the top text for the sticker:', text=self.top_text)
        if ok and text:
            self.top_text = text

    def enable_sticker_mode(self):
        self.sticker_mode = True
        bottom_text, ok = QtWidgets.QInputDialog.getText(self, 'Bottom Text', 'Enter the bottom text for the sticker:')
        if ok and bottom_text:
            self.bottom_text = bottom_text  # Store the bottom text
        else:
            self.sticker_mode = False  # Disable sticker mode if input was canceled

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and source is self.pdf_label:
            if self.sticker_mode:
                # Sticker mode is enabled, and a click has been detected on the PDF
                pos = event.pos()
                self.place_sticker(pos.x(), pos.y())
                self.sticker_mode = False  # Disable sticker mode after placing the sticker
                return True
        return super().eventFilter(source, event)

    def place_sticker(self, x, y):
        # Create the sticker image at a fixed resolution
        sticker_img = self.create_sticker(self.top_text, self.bottom_text)

        # Convert sticker image to pixmap
        sticker_bytes = io.BytesIO()
        sticker_img.save(sticker_bytes, format='PNG')
        sticker_bytes.seek(0)

        pixmap = fitz.Pixmap(sticker_bytes)

        # Get the current page
        page = self.doc.load_page(self.current_page)

        # Ensure the sticker is inserted without downscaling
        sticker_width = pixmap.width
        sticker_height = pixmap.height

        # Calculate the scaling factor from QLabel size to PDF page size
        scale_factor = page.rect.width / self.pdf_label.width()

        # Adjust the position based on scaling
        x_pdf = x * scale_factor
        y_pdf = y * scale_factor

        # Define the sticker position in the PDF with correct size
        rect = fitz.Rect(x_pdf, y_pdf, x_pdf + sticker_width, y_pdf + sticker_height)

        # Insert the sticker image into the PDF
        page.insert_image(rect, pixmap=pixmap)

        # Reload the PDF page after the sticker has been placed
        self.load_pdf()

    def create_sticker(self, top_text, bottom_text):
        # Create the sticker at a fixed size of 400x300 pixels for better clarity
        width, height = 100, 100  # Fixed sticker size

        # Create a high-resolution image for the sticker
        image = Image.new('RGB', (width, height), color='yellow')

        draw = ImageDraw.Draw(image)
        radius = 20  # Rounded corners radius
        draw.rounded_rectangle(
            [(0, 0), (width, height)],
            radius=radius,
            outline='black',
            width=6,  # Thicker outline for clarity
            fill='yellow'
        )

        # Try loading a custom font; if unavailable, use a fallback font
        try:
            # Make sure that the 'arial.ttf' file is in the right location or provide the path to a valid TTF font.
            font = ImageFont.truetype("arial.ttf", size=20)  # Larger text size for readability
        except IOError:
            # Fallback to default font if the custom font is not available
            font = ImageFont.load_default()

        # Draw the text using the custom font (if loaded) or default font
        draw.text((width / 2, height / 3), top_text, font=font, fill='black', anchor='mm')
        draw.text((width / 2, 2 * height / 3), bottom_text, font=font, fill='black', anchor='mm')

        return image

    def delete_stickers(self):
        try:
            # Get the current page
            page = self.doc.load_page(self.current_page)

            # Retrieve all images on the page
            images = page.get_images(full=True)

            # If no images are found, inform the user
            if not images:
                QtWidgets.QMessageBox.information(self, 'No Stickers Found', 'No stickers were found on this page.')
                return

            # Iterate over all images and attempt to delete them
            for img in images:
                xref = img[0]  # The first item in the tuple is the XREF of the image
                try:
                    page.delete_image(xref)
                    print(f"Deleted image with XREF {xref}")
                except Exception as e:
                    print(f"Failed to delete image with XREF {xref}: {e}")

            # Reload the PDF page after the stickers have been deleted
            self.load_pdf()
        
        except Exception as e:
            # Handle any unexpected errors and prevent the crash
            print(f"Error while deleting stickers: {e}")
            QtWidgets.QMessageBox.critical(self, 'Error', 'An error occurred while trying to delete stickers.')

    def save_pdf(self):
        options = QtWidgets.QFileDialog.Options()
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save PDF", os.path.basename(self.pdf_path), "PDF Files (*.pdf)", options=options)
        if save_path:
            self.doc.save(save_path)
            QtWidgets.QMessageBox.information(self, 'Success', f'PDF saved to {save_path}')

    def wheelEvent(self, event):
        # We still allow wheel-based zoom if Ctrl is pressed
        if event.modifiers() == QtCore.Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def zoom_in(self):
        self.zoom_level += 0.1  # Increase the zoom level by 10%
        self.display_pdf()

    def zoom_out(self):
        if self.zoom_level > 0.2:  # Prevent zooming out too much
            self.zoom_level -= 0.1  # Decrease the zoom level by 10%
        self.display_pdf()

    def event(self, event):
        if event.type() == QtCore.QEvent.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def gestureEvent(self, event):
        # Detect and handle pinch gesture for zooming
        if event.gesture(QtCore.Qt.PinchGesture):
            pinch = event.gesture(QtCore.Qt.PinchGesture)
            self.handlePinch(pinch)
            return True
        return False

    def handlePinch(self, pinch):
        # Handle pinch zoom gesture
        if pinch.changeFlags() & QtWidgets.QPinchGesture.ScaleFactorChanged:
            scale_factor = pinch.scaleFactor()
            self.zoom_level *= scale_factor
            if self.zoom_level < 0.2:  # Prevent excessive zoom-out
                self.zoom_level = 0.2
            self.display_pdf()

class PDFViewerApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PDF Viewer with Pinch Zoom and Scroll')

        # Create tab widget
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # Allow tabs to be closed
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        # Create menu
        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')

        open_action = QtWidgets.QAction('Open PDF(s)', self)
        open_action.triggered.connect(self.open_pdfs)
        file_menu.addAction(open_action)

        exit_action = QtWidgets.QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def open_pdfs(self):
        options = QtWidgets.QFileDialog.Options()
        pdf_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select PDF files", "", "PDF Files (*.pdf)", options=options)
        for pdf_path in pdf_paths:
            self.add_pdf_tab(pdf_path)

    def add_pdf_tab(self, pdf_path):
        tab = PDFTab(pdf_path)
        self.tabs.addTab(tab, os.path.basename(pdf_path))

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget is not None:
            widget.deleteLater()
        self.tabs.removeTab(index)

def main():
    app = QtWidgets.QApplication(sys.argv)
    viewer = PDFViewerApp()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()