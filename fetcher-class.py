#!/usr/bin/python3

import urllib.request, sys, os, argparse, re, threading

from urllib.parse import urlparse
from bs4 import BeautifulSoup
from queue import Queue

default_way = os.path.join(os.path.expanduser("~"), "acomics")

args_parser = argparse.ArgumentParser()
#args_parser.add_argument('-n', '--comics-name', type=str)
args_parser.add_argument('-u', '--comics-url', type=str)
args_parser.add_argument('-U', '--update-all', action='store_true', default=False, dest='update_all')
args_parser.add_argument('-f', '--force', action='store_true', default=False, dest='force')
args_parser.add_argument('-t', '--threads', type=int, default=10)
args_parser.add_argument('-d', '--output-dir', type=str, default=default_way)
args = args_parser.parse_args()

if not os.path.exists(args.output_dir):
		os.mkdir(args.output_dir)


# TODO
#+ refactor to class
#+ use threads
#+ use queue
#+ implement continuation
#+ add tracking list
# autopush on age restrictions button


class comicsFetcher(object):

	def __init__(self, comics_url, output_dir, threads=50, force=False):
		if not comics_url[-1] == "/":
			self.comics_url = comics_url + "/"
		else:
			self.comics_url = comics_url
		self.output_dir = output_dir
		self.threads = threads
		self.force = force
		self.URL = 'http://acomics.ru'


	def name_parse(self, comics_url):
		o = urlparse(comics_url)
		path = o.path.strip("/")
		return path[1:]


	def download(self, fetch_dir, queue):
		while not queue.empty():
			page_url = queue.get()
			#input(page_url)
			#print("Comics page URL:", page_url)
			try:
				url_read = urllib.request.urlopen(page_url)
				page_soup = BeautifulSoup(url_read.read(), 'html.parser')
				strip_number = int(page_soup.find("span", {"class": "issueNumber"}).getText().split("/")[0])
				strip_name = page_soup.find("span", {"class": "issueName"}).getText()
				if not strip_name == "":
					strip_name = "%d. %s" % (strip_number, strip_name)
				else:
					strip_name = str(strip_number)
				strip_path = os.path.join(fetch_dir, "%s.jpg" % (strip_name,) )
				
				img_url = self.URL + page_soup.find("img", {"id": "mainImage"})["src"]		
				#print("Image URL:", img_url)
			
				urllib.request.urlretrieve(img_url, strip_path)
			except Exception as e:
				print("Error while downloading %s.   Putting back in queue    %s" % (page_url, e))
				queue.put(page_url)
				continue

			print("№%s" % (strip_name,))


	def get_title_pages(self, comics_url):
		
		url_read = urllib.request.urlopen(comics_url)
		soup = BeautifulSoup(url_read.read(), 'html.parser')
		restrict = soup.find("form", {"class": "ageRestrict"})
		if restrict:
			print("This comics have an age restrictions!")
			sys.exit(1)
		strips_number = int(soup.find("span", {"class": "issueNumber"}).getText().split("/")[1])
		comics_title = soup.findAll("title")[0].getText()
		comics_title = comics_title[comics_title.index(" ")+1:comics_title.index(" читать")]
		return comics_title, strips_number


	def define_continuation(self, fetch_dir, strips_number):
		present_strips = [n.split("/")[-1].split(".")[0] for n in os.listdir(fetch_dir) if n != '']
		update_strips = []

		for n in range(1, strips_number+1):
			if not str(n) in present_strips:
				update_strips.append(n)

		return update_strips


	def run(self):
		comics_title, strips_number = self.get_title_pages(self.comics_url)
		fetch_dir = os.path.join(self.output_dir, comics_title)

		print("TITLE: %s" % comics_title)
		print("STRIPS: %d" % strips_number)

		# If comics is new
		if not os.path.exists(fetch_dir):
			print("New comics. Creating subfolder")
			os.mkdir(fetch_dir)
			strips_to_fetch = range(1, strips_number+1)
			with open(os.path.join(fetch_dir, ".url"), "w") as urlfile:
				urlfile.write(self.comics_url)
		else:
			strips_to_fetch = self.define_continuation(fetch_dir, strips_number)
			print("NEW STRIPS: %s" % len(strips_to_fetch))

		print()

		# If forced update
		if self.force:
			strips_to_fetch = range(1, strips_number+1)

		queue = Queue()
		for page_num in strips_to_fetch:
			page_url = self.comics_url + str(page_num)
			queue.put(page_url)

		threadlist = []
		for i in range(args.threads):
			t = threading.Thread(target=self.download, args=(fetch_dir, queue))
			t.start()
			threadlist.append(t)


def update_all_list(output_dir):
	URLs = []
	for comics_dir in os.listdir(output_dir):
		urlfile_path = os.path.join(output_dir, comics_dir, ".url")
		with open(urlfile_path, "r") as urlfile:
			URLs.append(urlfile.read())
	return URLs


def main():
	global args

	if args.update_all:
		for url in update_all_list(args.output_dir):
			comics = comicsFetcher(comics_url=url, 
								output_dir=args.output_dir,
								threads=args.threads,
								force=args.force)
			comics.run()
	elif args.comics_url:
		com = comicsFetcher(comics_url=args.comics_url, 
							output_dir=args.output_dir,
							threads=args.threads,
							force=args.force)
		com.run()
	else:
		print("Specify URL or -U argument")

if __name__ == '__main__':
	main()