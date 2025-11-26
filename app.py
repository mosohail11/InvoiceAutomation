from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer, Image, TableStyle, XPreformatted
from datetime import datetime, timedelta
import os
import json
import io

app = Flask(__name__)

# Generate dynamic invoice number and dates
invoice_counter_file = 'invoice_counter.json'

def get_next_invoice_number():
    """Get and increment invoice number"""
    if os.path.exists(invoice_counter_file):
        with open(invoice_counter_file, 'r') as f:
            data = json.load(f)
            invoice_number = data.get('last_invoice', 73) + 1
    else:
        invoice_number = 74

    # Save updated counter
    with open(invoice_counter_file, 'w') as f:
        json.dump({'last_invoice': invoice_number}, f)
    
    return invoice_number

def generate_invoice(items_data, customer_data=None):
    """Generate PDF invoice with given items and customer info"""
    # Default customer data if not provided
    if not customer_data:
        customer_data = {
            'name': 'John Doe',
            'address': '45 Elm Avenue',
            'city': 'Gotham, NY 10001'
        }
    
    # Get invoice details
    invoice_number = get_next_invoice_number()
    today = datetime.now()
    due_date = today + timedelta(days=15)
    
    invoice_no = f'INV-{today.year}-{invoice_number:03d}'
    invoice_date = today.strftime('%Y-%m-%d')
    due_date_str = due_date.strftime('%Y-%m-%d')
    
    # Create PDF in memory
    pdf_buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # Logo or company name
    logo_path = 'nn_logo.jpg'
    try:
        logo = Image(logo_path, width=35*mm, height=35*mm)
    except:
        logo = Paragraph('<b>ACME Corporation</b>', styles['Title'])
    
    company_info = XPreformatted(
        'ACME Corporation\n123 Market Street\nMetropolis, CA 94103\n+1 (555) 123-4567',
        styles['Normal']
    )
    
    header = Table([[logo, company_info]], colWidths=[60*mm, 100*mm])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    
    story += [header, Spacer(1, 20)]
    story += [Paragraph('<b>INVOICE</b>', styles['Title']), Spacer(1, 10)]
    
    # Invoice info
    invoice_info = [
        ['Invoice No:', invoice_no],
        ['Date:', invoice_date],
        ['Due Date:', due_date_str]
    ]
    
    customer_info = XPreformatted(
        f'{customer_data.get("name", "Customer")}\n{customer_data.get("address", "")}\n{customer_data.get("city", "")}',
        styles['Normal']
    )
    
    left = Table(invoice_info, colWidths=[70, 70])
    right = Table([[Paragraph('Bill To:', styles['Normal']), customer_info]], colWidths=[50, 120])
    
    info = Table([[left, right]], colWidths=[90*mm, 90*mm])
    info.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    
    story += [info, Spacer(1, 80)]
    
    # Items table
    items = [['Description', 'Qty', 'Unit Price', 'Tax', 'Total']]
    
    subtotal = 0
    total_tax = 0
    
    for item in items_data:
        description = item.get('description', '')
        qty = float(item.get('qty', 0))
        unit_price = float(item.get('price', 0))
        tax_rate = float(item.get('tax', 0)) / 100
        
        line_subtotal = qty * unit_price
        line_tax = line_subtotal * tax_rate
        line_total = line_subtotal + line_tax
        
        subtotal += line_subtotal
        total_tax += line_tax
        
        items.append([
            description,
            str(qty),
            f'${unit_price:.2f}',
            f'{item.get("tax", "0")}%',
            f'${line_total:.2f}'
        ])
    
    table = Table(items, hAlign='LEFT', colWidths=[200, 50, 70, 50, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke)
    ]))
    
    story += [table, Spacer(1, 80)]
    
    # Totals
    grand_total = subtotal + total_tax
    
    totals = [
        ['Subtotal:', f'${subtotal:.2f}'],
        ['Tax:', f'${total_tax:.2f}'],
        ['Total Due:', f'${grand_total:.2f}']
    ]
    
    totals_table = Table(totals, colWidths=[370, 70], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black)
    ]))
    
    story += [totals_table, Spacer(1, 30)]
    
    # Notes
    story.append(Paragraph('<b>Notes:</b>', styles['Heading3']))
    notes = (
        'Thank you for your business.'
        )
    story += [XPreformatted(notes, styles['Normal']), Spacer(1, 40)]
    story.append(Paragraph('© 2025 NextGen Gadgets', styles['Normal']))
    
    # Build PDF
    doc.build(story)
    pdf_buffer.seek(0)
    
    return pdf_buffer, invoice_no

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Calculate totals for items"""
    try:
        items = request.json.get('items', [])
        
        subtotal = 0
        total_tax = 0
        
        calculated_items = []
        
        for item in items:
            qty = float(item.get('qty', 0))
            price = float(item.get('price', 0))
            tax_rate = float(item.get('tax', 0)) / 100
            
            line_subtotal = qty * price
            line_tax = line_subtotal * tax_rate
            line_total = line_subtotal + line_tax
            
            subtotal += line_subtotal
            total_tax += line_tax
            
            calculated_items.append({
                'description': item.get('description', ''),
                'qty': qty,
                'price': price,
                'tax': item.get('tax', '0'),
                'line_total': line_total
            })
        
        grand_total = subtotal + total_tax
        
        return jsonify({
            'success': True,
            'items': calculated_items,
            'subtotal': f'{subtotal:.2f}',
            'tax': f'{total_tax:.2f}',
            'total': f'{grand_total:.2f}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/download', methods=['POST'])
def download():
    """Generate and download PDF invoice"""
    try:
        items = request.json.get('items', [])
        customer = request.json.get('customer', {})
        
        if not items:
            return jsonify({'success': False, 'error': 'No items provided'}), 400
        
        pdf_buffer, invoice_no = generate_invoice(items, customer)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{invoice_no}.pdf'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
