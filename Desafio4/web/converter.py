import os
import re
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd


RESULT_PREFIX = "RESULTADO_VR_MENSAL_"


def _parse_month_year_from_filename(filename: str) -> Optional[Tuple[str, str]]:
	"""Extract MM and YYYY from a filename like 'RESULTADO_VR_MENSAL_08_2025.csv'.

	Returns (MM, YYYY) if matched, otherwise None.
	"""
	m = re.match(rf"^{RESULT_PREFIX}(\d{2})_(\d{4})\.csv$", filename)
	if not m:
		return None
	return m.group(1), m.group(2)


def find_latest_result_csv(output_dir: str) -> Optional[str]:
	"""Return the most recent RESULTADO_VR_MENSAL_*.csv file path in output_dir.

	Returns None if not found.
	"""
	if not os.path.isdir(output_dir):
		return None
	candidates = [
		os.path.join(output_dir, f)
		for f in os.listdir(output_dir)
		if f.startswith(RESULT_PREFIX) and f.lower().endswith(".csv")
	]
	if not candidates:
		return None
	candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
	return candidates[0]


def _derive_mm_yyyy_from_mtime(path: str) -> Tuple[str, str]:
	"""Fallback: build (MM, YYYY) from file's modification time."""
	ts = os.path.getmtime(path)
	dt = datetime.fromtimestamp(ts)
	return f"{dt.month:02d}", f"{dt.year:04d}"


def _make_xlsx_name(mm: str, yyyy: str) -> str:
	"""Build the desired XLSX filename: 'VR MENSAL MM.YYYY.xlsx'"""
	return f"VR MENSAL {mm}.{yyyy}.xlsx"


def convert_latest_result_to_xlsx(output_dir: str, dest_dir: Optional[str] = None) -> str:
	"""Convert the latest RESULTADO_VR_MENSAL_*.csv found in output_dir to XLSX.

	- output_dir: directory where RESULTADO_VR_MENSAL_*.csv files are stored
	- dest_dir: where to write the resulting XLSX; if None, writes to output_dir

	Returns the absolute path of the generated XLSX file.
	Raises FileNotFoundError if no CSV result is found.
	Raises ImportError if an XLSX writer engine is not available.
	"""
	csv_path = find_latest_result_csv(output_dir)
	if not csv_path:
		raise FileNotFoundError("Nenhum arquivo 'RESULTADO_VR_MENSAL_*.csv' encontrado em output.")

	filename = os.path.basename(csv_path)
	parsed = _parse_month_year_from_filename(filename)
	if parsed:
		mm, yyyy = parsed
	else:
		# Fallback to file mtime if pattern didn't match
		mm, yyyy = _derive_mm_yyyy_from_mtime(csv_path)

	xlsx_name = _make_xlsx_name(mm, yyyy)
	target_dir = dest_dir or output_dir
	os.makedirs(target_dir, exist_ok=True)
	xlsx_path = os.path.join(target_dir, xlsx_name)

	# Read CSV with expected delimiter and encoding
	df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')

	# Try to write to XLSX. This typically requires 'openpyxl' or 'xlsxwriter'.
	try:
		df.to_excel(xlsx_path, index=False)
	except Exception as e:
		# Provide a clearer message for missing engine
		if 'openpyxl' in str(e).lower() or 'xlsxwriter' in str(e).lower():
			raise ImportError(
				"Falha ao exportar Excel. Instale um engine XLSX, por exemplo: 'pip install openpyxl'"
			) from e
		raise

	return xlsx_path

