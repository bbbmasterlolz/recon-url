from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.units import cm
from datetime import datetime

_styles = getSampleStyleSheet()


def print_results(all_results: list[list]):
    """Print test results to the console."""
    for result_group in all_results:
        for response in result_group:
            if hasattr(response, "status_code"):
                print(f"{response.url}")
                print(f"status  : {response.status_code}")
                print(f"allowed : {response.headers.get('Allow')}")
            else:
                print(response)
            print("")


def make_pdf(all_results: list[list], js_urls: list[str], main_url: str):
    """Generate a PDF report from test results."""
    date = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    file_name = output_dir / f"{main_url.replace('https://','').replace('http://','').split('/', 1)[0]}_{date}.pdf"
    pdf = SimpleDocTemplate(
        str(file_name),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    content = []

    # Main title
    content.append(
        Paragraph("API Report", _styles["Title"])
    )

    # One table per JS file's results
    for result, js in zip(all_results, js_urls):

        # Section heading
        content.append(
            Paragraph(
                f"API From {js}",
                _styles["Heading2"],
            )
        )
        content.append(Spacer(1, 10))

        data = [
            ["Status", "Methode", "URL"],
        ]

        for response in result:
            if hasattr(response, "status_code"):
                data.append([
                    response.status_code,
                    response.headers.get("Allow"),
                    Paragraph(response.url, _styles["BodyText"]),
                ])
            else:
                data.append([
                    "-",
                    "-",
                    Paragraph(response, _styles["BodyText"]),
                ])

        table = Table(
            data,
            colWidths=[
                1.5 * cm,   # Status
                5 * cm,     # Methode
                10.5 * cm,  # URL
            ],
        )

        table_style = [
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]

        # Blue background for rows with a real status
        for row_index, response in enumerate(result, start=1):
            if hasattr(response, "status_code"):
                table_style.append(
                    ("BACKGROUND", (0, row_index), (-1, row_index), colors.lightblue)
                )

        table.setStyle(TableStyle(table_style))

        content.append(table)
        content.append(Spacer(1, 25))

    pdf.build(content)
    print(f"\n[+] PDF saved to {file_name}")

