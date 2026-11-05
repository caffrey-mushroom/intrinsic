# The Map — model pipeline

Single source of truth is Excel in 坚果云 `AI Economy/The Map/`. The page only draws.

- `Map_Model_YYYY.MM.DD.xlsx` (newest wins), tabs:
  - **Nodes**: one row per dot (id = name shown on the map, sector, group, layer, private, market cap, role). Add a company = add a row.
  - **Links**: buyer → seller + note. These are the lines on the map.
  - **Wallet**: drivers copied from AI Economy Model (blue, source in column O), my assumptions, and the wallet formulas (code in column H).
  - **Sell / Buy**: share of each wallet earned / spent by each id. Line width = wallet × buyer share × seller share.
  - **Output / Check / Export**: AI revenue and AI spend per id per year; share sums; long `id | year | metric | value` table.
- Any other workbook in the same folder with an `Export` tab (same four columns) overrides the Map Model for the ids / years / metrics it covers. Files apply in name order.

Rebuild: stage the folder, then

    python3 tools/the-map/build_map.py <folder> --out map/data.json

Workbooks never opened in Excel have no cached values; the script recalculates them with LibreOffice first.
