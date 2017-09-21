import csv

#file = open('/home/vagrant/.virtualenvs/tsj-multi/src/tsj-gemstone/tsj_gemstone/tests/data/spicer.csv')
file = open('/home/ubuntu/.virtualenvs/tsj-mt/src/tsj-gemstone/tsj_gemstone/tests/data/spicer.csv')

reader = csv.reader(file)

count = 1

values = []

one_word = [
    'Lab',
    'Cert',
    'Carat',
    'Color',
    'Clarity',
    'Polish',
    'Symmetry',
    'Cut',
]

two_words = [
    'Diamond Shape',
    'Sarine Number',
    'Sarine Template',
]

"""
Harmony Loose Diamond With One 0.70Ct Round Brilliant Cut D Si1 Diamond Lab: GIA Cert: 6225820160 Sarine Number: AUPRDJ8M18G Sarine Template: SPRGCHRMD3 Carat: 0.7 Color: D Clarity: SI2 Cut: Very Good Polish: Very Good Symmetry: Very Good Diamond Shape: Oval
"""

for row in reader:
    dia = {}
    description = row[7]
    category = row[8]
    if category == '190':
        sections = description.split(': ')
        last_key = None
        for section in sections:
            if last_key:
                value = section.split()[:1][0]
                if value == 'Fire':
                    value = section.split()[1]
                dia[last_key] = value

            key = section.split()[-2:]
            key = ' '.join(key)
            if key in two_words:
                last_key = key
            else:
                key = section.split()[-1:][0]
                if key in one_word:
                    last_key = key
                else:
                    last_key = None

        print dia

    """
    for line in description:
        try:
            attr = line.split(': ')
            dia[attr[0]] = attr[1]
        except IndexError:
            attr = line.split(' ')
            try:
                if attr[6].startswith('Fire') or attr[6].startswith('Lazare'):
                    shape = attr[7]
                else:
                    shape = attr[6]
                print shape
            except IndexError:
                continue
            continue
    """
