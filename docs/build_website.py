import pathlib

import pdoc
import re
import os
import shutil
from pygments import highlight as pyg_highlight
from pygments.lexers import python as python_lexer
from pygments.formatters import html
from bs4 import BeautifulSoup, Tag

BUILD_FOLDER = 'docs/website/build'
SOURCE_FOLDER = 'docs/website/source'

import os

# theme from https://www.designbombs.com/freebie/prism/

t_p = pathlib.Path('website/source/templates')

# pdoc.render_helpers.lexer = python.Python3Lexer()
pdoc.render_helpers.formatter = html.HtmlFormatter(style='material')

formatter = html.HtmlFormatter(style='material')

def _highlight(src):
	lexer = python_lexer.Python3Lexer()
	formatter = html.HtmlFormatter(cssclass='highlight', style='material')
	output = pyg_highlight(src, lexer, formatter)
	return output
	# return Markup(output)

pdoc.render.configure(template_directory=t_p, docformat='numpy')
p  = pdoc.pdoc('LineDream', )

# root = 'https://linedream.marcrleonard.com/'
root = None
if not root:
	root = os.getenv('linedream_site', None) or f'http://localhost:63342/LineDream/docs/{BUILD_FOLDER}/'


# Use BS to swizzle the names and tags
_docs_soup = BeautifulSoup(p)

_title = _docs_soup.find('h2', text='API Documentation')
_title.name = 'h3'
_title.string.replace_with('Table of Contents')

nav = _docs_soup.find('nav')
nav.name = 'div'

docs = _docs_soup.find('main')
docs.name = 'div'

#######


from jinja2 import Environment, PackageLoader, FileSystemLoader, select_autoescape
env = Environment(
    loader = PackageLoader('website', 'source/templates'),
    # loader = FileSystemLoader(t_path),
    autoescape=select_autoescape()
)

os.makedirs(BUILD_FOLDER, exist_ok=True)

pages = [
	('', 'index.html'), # landing page
	('documentation', 'documentation.html'),
	('about', 'about.html'),
	('tutorials', 'getting_started.html'),
]

for path, template in pages:

	template_obj = env.get_template(template)

	f_name = 'index.html'
	if path:
		f_name = f'{path}/{f_name}'
		os.makedirs(f'{BUILD_FOLDER}/{path}', exist_ok=True)

	with open(f'{BUILD_FOLDER}/{f_name}', 'w') as f:
		f.write(template_obj.render({
			'url_root':root,
			'doc_nav': str(nav),
			'doc_main': str(docs)
		}))

# move css into the folder

folders_to_copy = [
	(f'{SOURCE_FOLDER}/css/', f'{BUILD_FOLDER}/css/'),
	(f'{SOURCE_FOLDER}/static/', f'{BUILD_FOLDER}/static/'),
	# ('website/build/css/', 'website/build/documentation/css/')	# TEMP COPY FOR EASE OF DEVELOPMENT

]

for source_dir, target_dir in folders_to_copy:

	file_names = os.listdir(source_dir)

	os.makedirs(target_dir, exist_ok=True)

	for file_name in file_names:

		original_file = pathlib.Path(source_dir, file_name)

		new_path = pathlib.Path(target_dir, file_name)

		if original_file.is_file():
			shutil.copy2(original_file, new_path)
		else:
			os.makedirs(new_path, exist_ok=True)

def isolated_exec(code_str):
	exec(code_str)


links = []

s = f'{SOURCE_FOLDER}/getting-started'
file_names = os.listdir(s)
	# os.makedirs(target_dir, exist_ok=True)

file_order = [file_name for file_name in file_names]
file_order.sort()

contents_order = []

for file in file_order:

	article_name = pathlib.Path(file).stem

	n = 0
	if '_' in article_name:
		n, article_name = article_name.split('_')

	rst_stuff = pathlib.Path(s, file).read_text()
	o = pdoc.markdown2.markdown(rst_stuff)

	soup = BeautifulSoup(o, parser='html.parser')
	pres = soup.find_all('pre')

	for c in pres:
		code = c.text

		made_output=False

		if str(code).endswith('#show_output\n'):
			code = code.replace('#show_output\n', '')

			lines = code.splitlines()

			print_line = None

			for idx, line in enumerate(lines):
				if 'Canvas.save(' in line:
					print_line = idx
					break

			if print_line:

				old_line = lines[print_line]

				if 'Canvas.save(f' in old_line:
					raise Exception("Please do not use f strings in the documentation examples, as it will confuse the build.")

				old_filename = old_line.replace('Canvas.save(', '').replace("'", '').replace('"', '').replace(')','')


				lines[print_line] = f'Canvas.save("{BUILD_FOLDER}/static/{old_filename}")'
				_code = '\n'.join(lines)
				isolated_exec(_code)
				made_output = True

		h = _highlight(code)
		_c = BeautifulSoup(h)
		c.replaceWith(_c)  # Put it where the A element is

		if made_output:
			new_tag = soup.new_tag("img")
			new_tag.append("some text here")
			# this means an image was rendered... Stick it into the parent
			# c.append(new_tag)


		# p.insert(0, c)  # put the A element inside the P (between <p> and </p>)

	# This will attempt to find a title in the three options.
	_titles = soup.find_all('h1')
	_titles.extend(soup.find_all('h2'))
	_titles.extend(soup.find_all('h3'))
	if _titles:
		article_name = _titles[0].text

	article_tag = article_name.replace(' ', '_')

	o = str(soup)

	contents_order.append((f'<li><a href="#{article_tag}">{article_name.title()}</a></li>', f'<div id={article_tag}>{o}</div>'))

article_names = [name for name, _ in contents_order]
articles = [content for _, content in contents_order]

os.makedirs(f'{BUILD_FOLDER}/getting-started', exist_ok=True)
with open(f'{BUILD_FOLDER}/getting-started/index.html', 'w') as f:

	template_obj = env.get_template('getting_started.html')



	f.write(template_obj.render({
		'url_root': root,
		'tut_articles': articles,
		'tut_contents': article_names
	}))


	# os.makedirs(target_dir, exist_ok=True)
