# app/convert_logo.py


import os
import cairosvg

output_path = "static/images/OES-Logo.pdf"

cairosvg.svg2pdf(
    url="static/images/oes-logo.svg",
    write_to=output_path
)

print(f"Done! Created {output_path}")