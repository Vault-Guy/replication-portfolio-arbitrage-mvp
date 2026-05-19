"""
Экспорт CSV-результатов в европейский формат (десятичный разделитель — запятая).

Вход:  все *.csv файлы из results/grid_search/.
Что делает: конвертирует числовые колонки: точка → запятая в качестве десятичного
            разделителя, чтобы файлы корректно открывались в Excel с европейской локалью.
            Проверяет, что количество строк не изменилось после конвертации.
Результат: results/grid_search_eu/<те же имена файлов> — копии с EU-форматированием.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sarb.utils.eu_export import export_eu_csv  # noqa: E402

INPUT_DIR = PROJECT_ROOT / "results" / "grid_search"
OUTPUT_DIR = PROJECT_ROOT / "results" / "grid_search_eu"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_paths = sorted(INPUT_DIR.glob("*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No CSV files found in {INPUT_DIR}")

    for csv_path in csv_paths:
        output_path = OUTPUT_DIR / csv_path.name
        input_rows, output_rows = export_eu_csv(csv_path, output_path)
        print(f"{csv_path.name}: input_rows={input_rows} output_rows={output_rows}")
        if input_rows != output_rows:
            raise ValueError(
                f"Row count mismatch for {csv_path.name}: "
                f"input_rows={input_rows} output_rows={output_rows}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
