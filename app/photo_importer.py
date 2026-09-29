import logging
import os
import re
import shutil
import threading
import time
from datetime import datetime

from PIL import Image
from PIL.ExifTags import TAGS

from app import app, db
from app.models import JournalEntry, JournalPhoto

logger = logging.getLogger('journal.photo_importer')

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
FILENAME_DATE_PATTERN = re.compile(r'(?P<y>(19|20)\d{2})[-_]?(?P<m>\d{2})[-_]?(?P<d>\d{2})')

class PhotoImporter(threading.Thread):
	def __init__(self, source_dir=None, dest_dir=None):
		self.source_dir = source_dir or app.config['PHOTO_SOURCE_DIR']
		self.dest_dir = dest_dir or os.path.join(app.static_folder, 'photos')
		self.photos_imported = 0
		self.photos_skipped = 0
		self.percent_complete = 0
		self._files = self._discover_files()
		self.total_entries_to_analyze = len(self._files)
		super().__init__()

	def run(self):
		start_time = time.monotonic()
		logger.info("Starting photo scan of %s (%d files found)", self.source_dir, self.total_entries_to_analyze)

		for index, file_path in enumerate(self._files):
			self._import_photo(file_path)
			self.percent_complete = float(index + 1) / float(self.total_entries_to_analyze)
		db.session.commit()
		if self.total_entries_to_analyze == 0:
			self.percent_complete = float(1) / float(1)

		elapsed = time.monotonic() - start_time
		logger.info(
			"Photo scan complete in %.2fs: %d imported, %d skipped",
			elapsed, self.photos_imported, self.photos_skipped)

	def _discover_files(self):
		if not os.path.isdir(self.source_dir):
			logger.info("Photo source directory %s does not exist, nothing to scan", self.source_dir)
			return []

		files = []
		for root, _, filenames in os.walk(self.source_dir):
			for filename in filenames:
				if os.path.splitext(filename)[1].lower() in IMAGE_EXTENSIONS:
					files.append(os.path.join(root, filename))
		return sorted(files)

	def _import_photo(self, file_path):
		photo_date = self._extract_date(file_path)
		if photo_date is None:
			logger.info("Skipping %s: no date found in EXIF or filename", file_path)
			self.photos_skipped += 1
			return

		entry = JournalEntry.query.filter_by(entry_date=photo_date).first()
		if entry is None:
			logger.info("Skipping %s: no journal entry for %s", file_path, photo_date)
			self.photos_skipped += 1
			return

		relative_path = self._copy_into_static(file_path, photo_date)
		if JournalPhoto.query.filter_by(file_path=relative_path).first():
			logger.debug("Skipping %s: already imported as %s", file_path, relative_path)
			self.photos_skipped += 1
			return

		photo = JournalPhoto(journal_entry_id=entry.id, file_path=relative_path)
		db.session.add(photo)
		self.photos_imported += 1
		logger.info("Imported %s for entry %s as %s", file_path, photo_date, relative_path)

	def _copy_into_static(self, file_path, photo_date):
		year_dir = os.path.join(self.dest_dir, str(photo_date.year))
		os.makedirs(year_dir, exist_ok=True)
		filename = "{}_{}".format(photo_date.isoformat(), os.path.basename(file_path))
		destination = os.path.join(year_dir, filename)
		if not os.path.exists(destination):
			shutil.copy2(file_path, destination)
		return os.path.join('photos', str(photo_date.year), filename)

	def _extract_date(self, file_path):
		exif_date = self._date_from_exif(file_path)
		if exif_date:
			return exif_date
		return self._date_from_filename(os.path.basename(file_path))

	def _date_from_exif(self, file_path):
		try:
			with Image.open(file_path) as image:
				exif = image.getexif()
		except Exception as error:
			logger.warning("Could not read EXIF from %s: %s", file_path, error)
			return None

		if not exif:
			return None

		for tag_id, value in exif.items():
			tag = TAGS.get(tag_id)
			if tag == 'DateTimeOriginal' or tag == 'DateTime':
				try:
					return datetime.strptime(value, '%Y:%m:%d %H:%M:%S').date()
				except (ValueError, TypeError):
					continue
		return None

	def _date_from_filename(self, filename):
		match = FILENAME_DATE_PATTERN.search(filename)
		if not match:
			return None
		try:
			return datetime(int(match.group('y')), int(match.group('m')), int(match.group('d'))).date()
		except ValueError:
			return None
