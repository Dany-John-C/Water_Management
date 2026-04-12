import os
import sqlite3
import csv
from datetime import datetime

DB_PATH = os.path.join('instance', 'water_management.db')
OUTPUT_DIR = 'exports'


def export_table(conn, table_name, output_path, order_by=None):
    cur = conn.cursor()

    # Get column names dynamically from the schema
    cur.execute(f"PRAGMA table_info({table_name})")
    columns_info = cur.fetchall()
    if not columns_info:
        print(f"[WARN] Table '{table_name}' does not exist or has no columns.")
        return

    column_names = [col[1] for col in columns_info]

    order_clause = f" ORDER BY {order_by}" if order_by else ""
    cur.execute(f"SELECT * FROM {table_name}{order_clause}")
    rows = cur.fetchall()

    if not rows:
        print(f"[INFO] Table '{table_name}' is empty; nothing to export.")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(rows)

    print(f"[OK] Exported {len(rows)} rows from '{table_name}' to '{output_path}'.")


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}. Make sure Flask has created it.")
        return

    conn = sqlite3.connect(DB_PATH)

    # Optional: timestamped prefix to distinguish runs
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Export sensor_readings (ordered by timestamp)
    export_table(
        conn,
        table_name='sensor_readings',
        output_path=os.path.join(OUTPUT_DIR, f'sensor_readings_{ts}.csv'),
        order_by='timestamp'
    )

    # Export leak_events (ordered by timestamp)
    export_table(
        conn,
        table_name='leak_events',
        output_path=os.path.join(OUTPUT_DIR, f'leak_events_{ts}.csv'),
        order_by='timestamp'
    )

    conn.close()


if __name__ == '__main__':
    main()
