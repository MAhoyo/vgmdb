import bs4

def parse_album_page(html_source):
	album_info = {}
	html_source = _fix_invalid_table(html_source)
	soup = bs4.BeautifulSoup(html_source)
	soup_profile = soup.find(id='innermain')
	soup_right_column = soup.find(id='rightcolumn')

	# parse names
	soup_names = soup_profile.h1
	album_info['name'] = _parse_names(soup_names)

	# main info header
	soup_info = soup_profile.find(id='rightfloat').div.div.table
	album_info.update(_parse_album_info(soup_info))

	# track list
	soup_tracklist = soup_profile.find_all('div', recursive=False)[-1]
	album_info['discs'] = _parse_tracklist(soup_tracklist)

	# stats
	album_info.update(_parse_right_column(soup_right_column))

	# notes
	soup_row = soup_profile
	while soup_row and soup_row.name != 'tr':
		soup_row = soup_row.parent
	if soup_row:
		soup_row = soup_row.find_next_sibling('tr')
		if soup_row:	# has a notes row
			soup_notes = soup_row.td.div.find_next_sibling('div').div
			notes = ''
			for child in soup_notes.children:
				if isinstance(child, bs4.Tag):
					if child.name == 'br':
						notes += '\n'
				else:
					notes += child.string
			album_info['notes'] = notes

	return album_info

def _fix_invalid_table(html_source):
	# fix missing </table>
	start = 0
	while True:
		start = html_source.find('<table', start+1)
		if start == -1:
			break
		prevtag_end = html_source.rfind('>', max(0,start-40), start)
		prevtag_start = html_source.rfind('<', max(0,start-40), prevtag_end)
		prevtag = html_source[prevtag_start:prevtag_end+1]
		if prevtag == '</tr>':
			html_source = html_source[:prevtag_end+1] + "</table>" + html_source[prevtag_end+1:]
			start = html_source.find('<table', prevtag_start)

	# fix duplicate </tr>
	start = 0
	while True:
		start = html_source.find('</tr>', start+1)
		if start == -1:
			break
		prevtag_end = html_source.rfind('>', max(0,start-40), start)
		prevtag_start = html_source.rfind('<', max(0,start-40), prevtag_end)
		prevtag = html_source[prevtag_start:prevtag_end+1]
		if prevtag == '</tr>':
			html_source = html_source[:prevtag_start] + html_source[prevtag_end+1:]
			start = prevtag_end
	return html_source

def _parse_names(soup_parent):
	info = {}
	if not soup_parent.span:
		info['en'] = soup_parent.string.strip()
	for soup_name in soup_parent.find_all('span', recursive=False):
		if not soup_name.has_key('lang'):
			continue
		lang = soup_name['lang'].lower()
		for child in soup_name.children:
			if not isinstance(child, bs4.Tag):
				name = child.string.strip()
		if soup_name.i:		# title has weird format
			name = soup_name.i.string.strip()
		info[lang] = name
	return info

def _parse_album_info(soup_info):
	album_info = {}
	soup_info_rows = soup_info.find_all('tr', recursive=False)
	for soup_row in soup_info_rows:
		name = soup_row.td.find('b').string
		soup_value = soup_row.td.find_next_sibling('td')
		names_single = {'Publish Format':'publish_format',
		                'Media Format':'media_format',
		                'Classification':'classification'}
		names_multiple = {'Composed by':'composers',
		                  'Arranged by':'arrangers',
		                  'Performed by':'performers',
		                  'Lyrics by':'lyricists'}

		if name == "Catalog Number":
			if soup_value.span:
				catalog = soup_value.span.a.string.strip()
			else:
				catalog = soup_value.string.strip()
			reprints = []
			for soup_reprint in soup_value.find_all('a'):
				note = None
				link = soup_reprint['href']
				if link[:len("http://vgmdb.net/")] == 'http://vgmdb.net/':
					link = link[len("http://vgmdb.net/"):]
				name = soup_reprint.string.strip()
				if name.find('(') != -1:
					left = name.find('(')
					right = name.find(')', left)
					note = name[left+1:right]
					name = name[:left].strip()
				if name == catalog:
					continue
				reprint_info = {"catalog": name, "link": link}
				if note:
					reprint_info['note']  = note
				reprints.append(reprint_info)
			album_info['catalog'] = catalog
			album_info['reprints'] = reprints
		elif name == "Release Date":
			date = soup_value.a['href'].split('#')[1]
			album_info['release_date'] = '%s-%s-%s'%(date[0:4], date[4:6], date[6:8])
		elif name == 'Release Price':
			price = soup_value.contents[0].strip()
			album_info['release_price'] = {"price":price}
			if price != 'Free':
				price = float(soup_value.contents[0])
				currency = soup_value.acronym.string.strip()
				album_info['release_price'] = {"price":price, "currency":currency}
		elif name == 'Published by':
			soup_links = soup_value.find_all('a')
			if len(soup_links) == 0:
				album_info['publishers'] = [{'name':soup_value.string.strip()}]
			if len(soup_links) > 0:
				album_info['publisher'] = {}
				album_info['publisher']['link'] = soup_links[0]['href']
				album_info['publisher']['name'] = _parse_names(soup_links[0])
			if len(soup_links) > 1:
				album_info['distributor'] = {}
				album_info['distributor']['link'] = soup_links[1]['href']
				album_info['distributor']['name'] = _parse_names(soup_links[1])
		elif name in names_single.keys():
			key = names_single[name]
			value = soup_value.string.strip()
			album_info[key] = value
		elif name in names_multiple.keys():
			key = names_multiple[name]
			value = []
			for soup_link in soup_value.find_all('a', recursive=False):
				link = {}
				link['link'] = soup_link['href']
				link['name'] = _parse_names(soup_link)
				value.append(link)
			album_info[key] = value
		else:
			# unknown key
			pass
	return album_info

def _parse_tracklist(soup_tracklist):
	discs = []
	soup_sections = soup_tracklist.find_all('div', recursive=False)
	languages = [li.a.string for li in soup_sections[0].ul.find_all('li', recursive=False)]
	soup_tabs = soup_sections[1].div.find_all('span', recursive=False)
	tab_index = -1
	for soup_tab in soup_tabs:
		tab_index += 1
		tab_language = languages[tab_index]
		index = 0
		soup_cur = soup_tab.span
		while soup_cur:
			disc_name = soup_cur.b.string
			soup_tracklist = soup_cur.find_next_sibling('table')
			soup_cur = soup_tracklist.find_next_sibling('span')
			disc_length = soup_cur.find_all('span')[-1].string
			if len(discs) < index+1:
				discs.append({})
			discs[index]['name'] = disc_name
			discs[index]['disc_length'] = disc_length
			if not discs[index].has_key('tracks'):
				discs[index]['tracks'] = []
			track_no = -1
			for soup_track in soup_tracklist.find_all('tr', recursive=False):
				track_no += 1
				soup_cells = soup_track.find_all('td')
				track_name = soup_cells[1].string
				track_length = soup_cells[2].span.string
				if len(discs[index]['tracks']) < track_no + 1:
					discs[index]['tracks'].append({'name':{},'track_length':track_length})
				discs[index]['tracks'][track_no]['name'][tab_language] = track_name
			soup_cur = soup_cur.find_next_sibling('span')
			index += 1
	return discs

def _parse_right_column(soup_right_column):
	album_info = {}
	soup_div = soup_right_column.div
	while soup_div:
		soup_section = soup_div.find_next_sibling('div')
		if soup_div.div.h3:
			section_title = soup_div.div.h3.string
			if section_title == 'Album Stats':
				album_info.update(_parse_section_album_stats(soup_section.div))
			if section_title == 'Related Albums':
				album_info['related'] = _parse_section_related_albums(soup_section.span)
			if section_title == 'Available at':
				album_info['stores'] = _parse_section_stores(soup_section.div)
			if section_title == 'Websites':
				album_info['websites'] = _parse_section_websites(soup_section.div)
			if section_title == 'Covers':
				# frickin covers section is different format
				soup_section = soup_div.find('div', id='cover_gallery')
				# do the parsing
				album_info['covers'] = _parse_section_covers(soup_section)
				#import ipdb; ipdb.set_trace()
				soup_section = soup_div.find_next_sibling()	# allow the next_sibling loop to work
				if not soup_section:
					soup_section = soup_div
				pass
			soup_div = soup_section.find_next_sibling('div')
		else:
			# found entry stats
			soup_section = soup_div.div
			album_info.update(_parse_section_info(soup_section))
			soup_div = None
			pass
	return album_info

def _parse_section_album_stats(soup_section):
	album_info = {}
	soup_divs = soup_section.find_all('div', recursive=False)
	soup_rating = soup_divs[0].find_all('span', recursive=False)
	if len(soup_rating) <= 1:
		album_info['votes'] = 0
	else:
		splits = soup_rating[1].string.split()
		if splits[0] == 'Nobody':
			album_info['votes'] = 0
		else:
			album_info['rating'] = float(splits[1])
			album_info['votes'] = int(splits[3])

	for soup_div in soup_divs[1:]:
		if not soup_div.b:
			continue
		div_name = soup_div.b.string.strip()
		div_value = None
		for child in soup_div.children:
			if not isinstance(child, bs4.Tag):
				div_value = child.string.strip()
		if div_name == 'Category':
			album_info['category'] = div_value
		if div_name == 'Products represented':
			album_info['products'] = []
			for soup_product in soup_div.find_all('a', recursive=False):
				product = {}
				product['link'] = soup_div.a['href']
				product['name'] = _parse_names(soup_div.a)
				album_info['products'].append(product)
		if div_name == 'Platforms represented':
			album_info['platforms'] = [plat.strip() for plat in div_value.split(',')]
	return album_info

def _parse_section_related_albums(soup_div):
	albums = []
	for soup_album in soup_div.find_all('div', recursive=False):
		date = None
		if soup_album.ul:		# if there are thumbnails
			soup_rows = soup_album.ul.find_all('li', recursive=False)
			catalog = soup_rows[1].span.string.strip()
			names = _parse_names(soup_rows[0].a)
			album_type = soup_rows[0].a['class'][-1].split('-')[1]
			date = _parse_album_info_time(soup_rows[2].string.strip())
			link = soup_rows[0].a['href']
			if link[:len("http://vgmdb.net/")] == 'http://vgmdb.net/':
				link = link[len("http://vgmdb.net/"):]
		else:
			catalog = soup_album.span.string
			names = _parse_names(soup_album.a)
			album_type = soup_album.a['class'][-1].split('-')[1]
			link = soup_album.a['href']
			if link[:len("http://vgmdb.net/")] == 'http://vgmdb.net/':
				link = link[len("http://vgmdb.net/"):]

		album = {}
		album['catalog'] = catalog
		album['link'] = link
		album['type'] = album_type
		album['name'] = names
		if date:
			album['date'] = date

		albums.append(album)
	return albums

def _parse_section_stores(soup_stores):
	""" Given an array of divs containing website information """
	soup_links = soup_stores.find_all('a', recursive=False)
	links = []
	for soup_link in soup_links:
		link = soup_link['href']
		name = soup_link.string
		if link[0:9] == '/redirect':
			slashpos = link.find('/', 10)
			link = 'http://'+link[slashpos+1:]
		links.append({"link":link,"name":name})
	return links

def _parse_section_websites(soup_websites):
	""" Given an array of divs containing website information """
	sites = {}
	for soup_category in soup_websites.find_all('div', recursive=False):
		category = soup_category.b.string
		soup_links = soup_category.find_all('a', recursive=False)
		links = []
		for soup_link in soup_links:
			link = soup_link['href']
			name = soup_link.string
			if link[0:9] == '/redirect':
				slashpos = link.find('/', 10)
				link = 'http://'+link[slashpos+1:]
			links.append({"link":link,"name":name})
		sites[category] = links
	return sites

def _parse_section_covers(soup_covers):
	""" Given an array of tables """
	covers = []
	for soup_table in soup_covers.find_all('table', recursive=False):
		for soup_row in soup_table.find_all('tr'):
			for soup_cell in soup_row.find_all('td'):
				soup_link = soup_cell.a
				if not soup_link:
					continue
				medium_link = soup_cell.a['href']
				full_link = medium_link.replace('-medium', '')
				thumb_link = medium_link.replace('-medium', '-thumb')
				name = soup_cell.a.h4.string.strip()
				cover = {"name":name, "thumb":thumb_link, \
				         "medium":medium_link, "full":full_link}
				covers.append(cover)
	return covers

def _parse_section_info(soup_section):
	album_info = {}
	soup_divs = soup_section.find_all('div', recursive=False)
	for soup_div in soup_divs:
		label = soup_div.b.string.strip()
		if label == 'Added':
			date = soup_div.br.next.string.strip()
			time = soup_div.span.string.strip()
			time = _parse_album_info_time("%s %s"%(date, time))
			album_info['added_date'] = time
		if label == 'Edited':
			date = soup_div.br.next.string.strip()
			time = soup_div.span.string.strip()
			time = _parse_album_info_time("%s %s"%(date, time))
			album_info['edited_date'] = time
		if label == 'Page traffic':
			soup_rows = soup_div.find_all('span', recursive=False)
			try:
				album_info['visitors'] = int(soup_rows[0].string.strip())
				album_info['freedb'] = int(soup_rows[1].string.strip())
			except:
				pass	# who puts a not-number in a page counter?
	return album_info

def _parse_album_info_time(time):
	months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', \
	          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
	month = time[0:3]
	month = months.index(month) + 1
	comma = time.find(',')
	day = int(time[4:comma])
	year = int(time[comma+2:comma+2+4])
	timepos = comma+2+4+1
	if timepos >= len(time):		# there is not a time to parse
		return "%02d-%02d-%02d"%(year,month,day)
	else:
		hour = int(time[timepos:timepos+2])
		minute = int(time[timepos+3:timepos+5])
		ampm = time[timepos+6:timepos+8]
		if ampm == 'PM':
			hour += 12
		return "%02d-%02d-%02dT%02d:%02d"%(year,month,day,hour,minute)
