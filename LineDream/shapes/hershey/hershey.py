# Copyright 2011-2016, Windell H. Oskay, www.evilmadscientist.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Modified by Sheldon B. Michaels to allow increased precision in placement
#	of characters, and to allow user to create a line of text for a viewing
#	comparison in each and every font.  May 2016
#	shel at shel dot net
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# from lxml import etree

from .aux_hershey import hersheydata
from .aux_hershey import inkex
from .aux_hershey import simplestyle

Debug = True
FONT_GROUP_V_SPACING = 45   # all the fonts are nearly identical in height, so a constant
							# spacing is adequate, and is arbitrary - just so it looks good



class Hershey( inkex.Effect ):
	def __init__( self ):
		inkex.Effect.__init__( self )
		# self.OptionParser.add_option( "--tab",  #NOTE: value is not used.
		# 	action="store", type="string",
		# 	dest="tab", default="splash",
		# 	help="The active tab when Apply was pressed" )
		# self.OptionParser.add_option( "--text",
		# 	action="store", type="string",
		# 	dest="text", default="Hershey Text for Inkscape",
		# 	help="The input text to render")
		# self.OptionParser.add_option( "--action",
		# 	action="store", type="string",
		# 	dest="action", default="render",
		# 	help="The active option when Apply was pressed" )
		# self.OptionParser.add_option( "--fontface",
		# 	action="store", type="string",
		# 	dest="fontface", default="rowmans",
		# 	help="The selected font face when Apply was pressed" )

		self.text_output_str = None
		self.text_output_obj = None

		self.letter_paths = []

	def effect( self, text, fontface ):
		
		self.text = text
		self.action = 'render'
		self.fontface  = fontface
		
		OutputGenerated = False

		g = None

		# Group generated paths together, to make the rendered letters easier to manipulate in Inkscape.
		g_attribs = {inkex.addNS('label','inkscape'):'Hershey Text' }
		# g = inkex.etree.SubElement(self.current_layer, 'g', g_attribs)

		style = { 'stroke' : '#000000', 'fill' : 'none', 'stroke-linecap' : 'round', 'stroke-linejoin' : 'round' }
		# Apply rounding to ends so that user gets best impression of final printed text appearance.
		# g.set( 'style',simplestyle.formatStyle(style))

		font = eval('hersheydata.' + str(self.fontface))
		clearfont = hersheydata.futural  
		#Baseline: modernized roman simplex from JHF distribution.
		
		w = 0  #Initial spacing offset
		spacing = 3  # spacing between letters

		if self.action == "render":
			#evaluate text string and render in the chosen font

			letters = []
			for letter in self.text:
				letters.append(ord(letter)-32)

			letterVals = [ord(q) - 32 for q in self.text]
			for idx, q in enumerate(letterVals):
				letter = self.text[idx]
				if (q <= 0) or (q > 95):
					w += 2*spacing
				else:
					_paths, midpoint, offset = self.letter_path(q, font, w, 0, g)
					self.letter_paths.append( {
						'letter':letter,
						'midpoint': midpoint,
						'offset': offset,
						'paths':_paths
					})

					w = self.draw_svg_text(q, font, w, 0, g)
					OutputGenerated = True
			# t = 'translate(' + str(self.view_center[0] - w/2) + ',' + str(self.view_center[1]) + ')'
			# g.set( 'transform',t)
		# elif self.options.action == 'sample':
		# 	t = self.render_table_of_all_fonts( 'group_allfonts', g, spacing, clearfont )
		# 	g.set( 'transform',t)
		# 	OutputGenerated = True
		# else:
		# 	#Generate glyph table for a single font
		# 	wmax = 0;
		# 	for p in range(0,10):
		# 		w = 0
		# 		v = spacing * (15*p - 67 )
		# 		for q in range(0,10):
		# 			r = p*10 + q
		# 			if (r < 0) or (r > 95):
		# 				w += 5*spacing
		# 			else:
		# 				w = self.draw_svg_text(r, clearfont, w, v, g)
		# 				w = self.draw_svg_text(r, font, w, v, g)
		# 				w += 5*spacing
		# 		if w > wmax:
		# 			wmax = w
		# 	w = wmax
		# 	#  Translate group to center of view, approximately
		# 	t = 'translate(' + str( self.view_center[0] - w/2) + ',' + str( self.view_center[1] ) + ')'
		# 	g.set( 'transform',t)
		# 	OutputGenerated = True

		if not OutputGenerated:
			self.current_layer.remove(g)	#remove empty group, if no SVG was generated.


		# self.text_output_str = (etree.tostring(g, pretty_print=True)).decode('utf-8')
		# self.text_output_obj = g

	def getDocHeight( self):
		doc_height = self.unittouu(self.document.getroot().get('height'))
		return doc_height

	def render_table_of_all_fonts( self, fontgroupname, parent, spacing, clearfont ):
		v = 0
		wmax = 0
		wmin = 0
		fontgroup = eval( 'hersheydata.' + fontgroupname )
		
		# Render list of font names in a vertical column:
		nFontIndex = 0
		for f in fontgroup:
			w = 0
			letterVals = [ord(q) - 32 for q in (f[1] + ' -> ')]
			# we want to right-justify the clear text, so need to know its width
			for q in letterVals:
				w = self.svg_text_width(q, clearfont, w)
				
			w = -w                      # move the name text left by its width
			if w < wmin:
				wmin = w
			# print the font name
			for q in letterVals:
				w = self.draw_svg_text(q, clearfont, w, v, parent)
			v += FONT_GROUP_V_SPACING
			if w > wmax:
				wmax = w
			
		# Next, we render a second column. The user's text, in each of the different fonts:
		v = 0                   # back to top line
		wmaxname = wmax + 8     # single space width
		for f in fontgroup:
			w = wmaxname
			font = eval('hersheydata.' + f[0])
			#evaluate text string
			letterVals = [ord(q) - 32 for q in self.text]
			for q in letterVals:
				if (q < 0) or (q > 95):
					w += 2*spacing
				else:
					w = self.draw_svg_text(q, font, w, v, parent)
			v += FONT_GROUP_V_SPACING
			if w > wmax:
				wmax = w

		heightAsFractionOfPageSize = 0.95	#Scale to somewhat less than full document height
		scaleFactor = (heightAsFractionOfPageSize * self.getDocHeight() / v)
		#  return string that scales group to document height, and translates group to center of view, approximately
		t = 'translate(' + str(self.view_center[0]) + ',' + str(self.view_center[1] - scaleFactor * v / 2 ) + ')'
		t += 'scale(' + str( scaleFactor) + ')'
		return t

	def letter_path(self, char, face, offset, vertoffset, parent):
		## THIS IS A PARSER
		pathString = face[char]
		splitString = pathString.split()
		midpoint = offset - float(splitString[0])
		pathString = pathString[pathString.find("M"):]  # portion after first move

		vs = [

		]

		ss = pathString.split(' ')

		p = []
		x=None
		for s in ss:
			if s == 'M':
				if len(p)>0:
					vs.append(p)
					p=[]
			else:
				if s == 'L':
					continue

				if x != None:
					p.append((x,float(s)))
					x=None

				else:
					x=float(s)
		if len(p) > 0:
			vs.append(p)


		# print(vs)

		return vs, midpoint, offset


	def draw_svg_text(self, char, face, offset, vertoffset, parent):
		## THIS IS A PARSER
		pathString = face[char]
		splitString = pathString.split()
		midpoint = offset - float(splitString[0])
		pathString = pathString[pathString.find("M"):]  # portion after first move
		trans = 'translate(' + str(midpoint) + ',' + str(vertoffset) + ')'
		text_attribs = {'d': pathString, 'transform': trans}
		# inkex.etree.SubElement(parent, inkex.addNS('path', 'svg'), text_attribs)
		return midpoint + float(splitString[1])  # new offset value

	def svg_text_width(self, char, face, offset):
		pathString = face[char]
		splitString = pathString.split()
		midpoint = offset - float(splitString[0])
		return midpoint + float(splitString[1])  # new offset value


if __name__ == '__main__':
	# {'action': 'render', 'text': 'Blah!', 'fontface': 'futuram', 'tab': '"splash"'}
	# aa = ['hershey.py', '--tab="splash"', '--text=l', '--action=render', '--fontface=futural', '/Users/marcleonard/Projects/plotplanner/svgs/tree_test_text.svg']
	aa = ['hershey.py', '--tab="splash"', '--text=Blah!', '--action=render', '--fontface=futural', '/Users/marcleonard/Projects/plotplanner/svgs/tree_test_text.svg']
	# aa = ['hershey.py', '--tab="splash"', '--text=Blah!', '--action=render', '--fontface=futuram', '/Users/marcleonard/Projects/plotplanner/svgs/tree_test_text.svg']
	e = Hershey()
	# e.affect()
	e.effect('Blah!', 'futural')
	# print(e.text_output_obj)
	# print(e.text_output_str)
	import json
	print(json.dumps(e.letter_paths, indent=4))

