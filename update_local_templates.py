
env = self.env
templates = env['whatsapp.template'].search([('name', 'ilike', 'Showline Template')])
count = 0
for tmpl in templates:
    if '{{1}}' in tmpl.body:
        new_body = tmpl.body.replace('Hi {{1}}, ', 'Hi, ').replace('{{1}}', '')
        tmpl.write({'body': new_body})
        count += 1
        print(f"Updated local template ID {tmpl.id}: '{tmpl.name}'")

print(f"Total local templates updated: {count}")
env.cr.commit()
