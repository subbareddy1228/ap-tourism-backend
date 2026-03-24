import csv
import io
from fastapi.responses import StreamingResponse


def to_csv_response(data: list, filename: str = "report.csv") -> StreamingResponse:
    if not data:
        raise ValueError("No data to export")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
