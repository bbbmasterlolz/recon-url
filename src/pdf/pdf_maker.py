from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.units import cm

styles = getSampleStyleSheet()


def make_pdf(results, js_url):
    pdf = SimpleDocTemplate(
        "output.pdf",
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm
    )

    content = []

    # Main title
    content.append(
        Paragraph("API Report", styles["Title"])
    )

    # One table per result
    for result, js in zip(results, js_url):

        # Text before each table
        content.append(
            Paragraph(
                f"API From {js}",
                styles["Heading2"]
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
                    Paragraph(response.url, styles["BodyText"])
                ])
            else:
                data.append([
                    "-",
                    "-",
                    Paragraph(response, styles["BodyText"])
                ])

        table = Table(
            data,
            colWidths=[
                1.5 * cm,   # Status
                5 * cm,     # Methode
                10.5 * cm   # URL
            ])

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