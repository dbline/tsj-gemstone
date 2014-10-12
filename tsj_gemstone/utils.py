import csv
from decimal import Decimal
from importlib import import_module

IMPORTER_MODULES_PACKAGE = 'tsj_gemstone.backends'

def get_backend(mod):
    m = import_module('%s.%s' % (IMPORTER_MODULES_PACKAGE, mod))

    return m

def _excel_header(fn):
    # TODO: Move import to module level once xlrd is installed on all sites
    import xlrd

    wb = xlrd.open_workbook(file_contents=open(fn, 'rb').read())
    sheet = wb.sheets()[0]
    line = []
    for col in range(sheet.ncols):
        line.append(sheet.cell(0, col).value)
    return line

def _csv_header(fn):
    reader = csv.reader(open(fn))
    return reader.next()

def get_header_row(fn):
    if fn.lower().endswith('xls') or fn.lower().endswith('xlsx'):
        row = _excel_header(fn)
    if fn.lower().endswith('csv') or fn.lower().endswith('tsv'):
        row = _csv_header(fn)

    if row:
        # Trim blank columns
        row = [col for col in row if col]

    return row

def detect_backend(filename):
    SHEET_TYPES = {
        'emperor': ['DiamondID', 'Shape', 'Weight', 'Color', 'Clarity', 'askingPrice', 'Measurements', 'Cut', 'Lab', 'RapnetDiscountPercent', 'IndexPrice', 'IndexPriceDiscount', 'DepthPercent', 'TablePercent', 'GirdleMin', 'GirdleMax', 'GirdlePercent', 'GirdleCondition', 'CuletSize', 'CuletCondition', 'Polish', 'Symmetry', 'FluorescenceIntensity', 'FluorescenceColor', 'CrownHeight', 'CrownAngle', 'PavilionDepth', 'PavilionAngle', 'Enhancement', 'LaserInscription', 'FancyColor', 'FancyColorIntensity', 'FancyColorOvertone', 'Member Comments', 'Cert Comment', 'CertificateID', 'CertificateImage', 'ImageFile', 'SarinFile', 'VendorStockNumber', 'MatchingVendorStockNumber', 'IsMatchedPairSeparable', 'CityLocation', 'StateLocation', 'CountryLocation', 'ParcelStoneCount', 'Availability', 'TradeShow', 'ClientRowID'],
        'gndiamond': ['SHAPE', 'SIZE', 'COLOR', 'CLARITY', 'CUT GRADE', 'PRICE', 'OFFRAPAPORT', 'CERT', 'DEPTH%', 'TABLE%', 'GIRDLE', 'CULET', 'POLISH', 'FLUORESCENCE INTENSITY', 'SYMMETRY', 'DiamondBrand', 'CROWN', 'PAVILION', 'MEASUREMENTS', 'COMMENT', 'STONES', 'CERT#', 'STOCK#', 'PAIR', ' PAIR SEPARABLE', 'FANCYCOLOR', 'TRADE SHOW', 'CERTIFICATE#', 'SHOWCERT', 'FancyMainColorBody'],
        'hasenfeld': ['Shape', 'Size', 'Color', 'Clarity', 'Price Per Carat', 'LAB', 'Depth %', 'Table', 'Girdle', 'Culet', 'Polish', 'Symmetry', 'Fluorescence', 'Inventory', 'Measurements', 'Lab Number', 'Disc', 'Cut Grade', 'CertURL'],
        'mkdiamonds': ['Shape', 'Weight', 'Color', 'Clarity', 'Measurements', 'Cut Grade', 'Lab', 'Price', 'Depth %', 'Table %', 'Girdle Thin', 'Girdle Thick', 'Girdle %', 'Culet Size', 'Culet Condition', 'Polish', 'Symmetry', 'Fluorescence Intensity', 'Fluorescence Color', 'Crown Height', 'Crown Angle', 'Pavilion Depth', 'Pavilion Angle', 'Treatment', 'LaserInscription', 'Comments', 'Certificate #', 'CertificateImage', 'VendorStockNumber', 'MatchedPairStockNumber', 'IsMatchedPairSeparable', 'FancyColor', 'FancyColorIntensity', 'FancyColorOvertone', 'ParcelStoneCount', 'TradeShow', 'Cash Price', 'Availability', 'RapLink', 'DiamondImage', 'City', 'State', 'Country'],
        'rapaport': ['Lot #', 'Owner', 'Shape', 'Carat', 'Color', 'Clarity', 'Cut Grade', 'Price', '%/Rap', 'Cert', 'Depth', 'Table', 'Girdle', 'Culet', 'Polish', 'Sym', 'Fluor', 'Meas', 'Comment', '# Stones', 'Cert #', 'Stock #', 'Make', 'Date', 'City', 'State', 'Country', 'Image'],
        'rapnet10': ['Seller', 'RapNet Seller Code', 'Shape', 'Weight', 'Color', 'Fancy Color', 'Fancy Intensity', 'Fancy Overtone', 'Clarity', 'Cut Grade', 'Polish', 'Symmetry', 'Fluorescence', 'Measurements', 'Lab', 'Cert #', 'Stock #', 'Treatment', 'RapNet Price', 'RapNet Discount Price', 'Depth %', 'Table %', 'Girdle', 'Culet', 'Comment', 'City', 'State', 'Country', 'Is Matched Pair Separable', 'Pair Stock #', 'Parcel number of stones', 'Certificate URL', 'RapNet Lot #', 'Date'],
        'rdi': ['Allow RapLink Feed', 'Availability', 'Black Inclusion', 'Brand', 'Cash Discount %', 'Cash Price', 'Center Inclusion', 'Cert Comment', 'Certificate #', 'Certificate Filename', 'City', 'Clarity', 'Color', 'Country', 'Crown Angle', 'Culet Condition', 'Culet Size', 'Cut Grade', 'Depth %', 'Diamond Image', 'Display Cert Number', 'Fancy Color', 'Fancy Color Intensity', 'Fancy Color Overtone', 'Fluorescence Color', 'Fluorescence Intensity', 'Girdle %', 'Girdle Condition', 'Girdle Thick', 'Girdle Thin', 'Is Matched Pair Separable', 'Key To Symbols', 'Lab', 'Laser Inscription', 'MeasDepth', 'MeasLength', 'Measurements', 'MeasWidth', 'Member Comments', 'Pair Stock #', 'Parcel Stones', 'Pavilion Angle', 'Pavilion Depth', 'Polish', 'RapNet Discount %', 'RapNet Price', 'Report Issue Date', 'Report Issue Location', 'Report Type', 'Shade', 'Shape', 'ShowOnlyOnRapLink', 'Size', 'Star Length', 'State', 'Stock #', 'Symmetry', 'Table %', 'Trade Show', 'Treatment'],
        'polygon': ['Supplier ID', 'Shape', 'Weight', 'Color', 'Clarity', 'Price / Carat', 'Lot Number', 'Stock Number', 'Lab', 'Cert #', 'Certificate Image', '2nd Image', 'Dimension', 'Depth %', 'Table %', 'Crown Angle', 'Crown %', 'Pavilion Angle', 'Pavilion %', 'Girdle Thinnest', 'Girdle Thickest', 'Girdle %', 'Culet Size', 'Culet Condition', 'Polish', 'Symmetry', 'Fluor Color', 'Fluor Intensity', 'Enhancements', 'Remarks', 'Availability', 'Is Active', 'FC-Main Body', 'FC- Intensity', 'FC- Overtone', 'Matched Pair', 'Separable', 'Matching Stock #', 'Pavilion', 'Syndication', 'Cut Grade', 'External Url'],
        'varsha': [u'LOT NO', u'SHAPE', u'CARAT', u'COLOR', u'CLARITY', u'MEASUREMENT', u'DEPT ', u'TBL ', u'CUT', u'CUL', u'POL', u'SYM', u'FL', u'GIRDLE', u'LAB', u'PRICE / CT', u'TOTAL '],
        'whitediamond': ['Shape', 'Carat', 'Color', 'Clarity', 'Measurements', 'Cut', 'Cert Type', 'Per Carat', 'Depth', 'Table', 'Girdle', 'Culet', 'Polish', 'Symmetry', 'Fluorescence', 'Cert Number', 'Cert Image', 'Stock Number', 'Supplier Name', 'Email', 'DiaImage'],
    }

    header = get_header_row(filename)
    for format, row in SHEET_TYPES.items():
        if header == row:
            return format

def moneyfmt(value, places=2, curr='$', sep=',', dp='.', pos='', neg='-', trailneg=''):
    """Convert Decimal to a money formatted string.

    places:  required number of places after the decimal point
    curr:    optional currency symbol before the sign (may be blank)
    sep:     optional grouping separator (comma, period, space, or blank)
    dp:      decimal point indicator (comma or period)
             only specify as blank when places is zero
    pos:     optional sign for positive numbers: '+', space or blank
    neg:     optional sign for negative numbers: '-', '(', space or blank
    trailneg:optional trailing minus indicator:  '-', ')', space or blank

    >>> d = Decimal('-1234567.8901')
    >>> moneyfmt(d, curr='$')
    '-$1,234,567.89'
    >>> moneyfmt(d, places=0, sep='.', dp='', neg='', trailneg='-')
    '1.234.568-'
    >>> moneyfmt(d, curr='$', neg='(', trailneg=')')
    '($1,234,567.89)'
    >>> moneyfmt(Decimal(123456789), sep=' ')
    '123 456 789.00'
    >>> moneyfmt(Decimal('-0.02'), neg='<', trailneg='>')
    '<0.02>'

    """
    q = Decimal(10) ** -places      # 2 places --> '0.01'
    sign, digits, exp = value.quantize(q).as_tuple()
    result = []
    digits = map(str, digits)
    build, next = result.append, digits.pop
    if sign:
        build(trailneg)
    for i in range(places):
        build(next() if digits else '0')
    build(dp)
    if not digits:
        build('0')
    i = 0
    while digits:
        build(next())
        i += 1
        if i == 3 and digits:
            i = 0
            build(sep)
    build(curr)
    build(neg if sign else pos)
    return ''.join(reversed(result))
