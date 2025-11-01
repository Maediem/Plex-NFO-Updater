# Plex-NFO-Updater

---

A Python Script that scans local media directories for .nfo and applies metadata such as title, summary, actors and posters updates to matching movies or shows (including seasons and episodes).

This README describes what the script, how to configure it, how to run it, etc.

> ✅ Worked on Linux with my serie with NFO files. I did not try for other type (e.g. movies and music).

---

## Disclaimer

This utility updates Plex Media Server metadata using information provided in NFO files. NFO examples included here are illustrative; users may create and use their own NFOs to supply custom descriptions or metadata when official sources are incomplete or unsatisfactory. This project was also created for educational and learning purposes, particularly to explore and demonstrate usage of the plexapi library and metadata management in Plex. It is intended for lawful, personal use only and does not support or facilitate illegal distribution or piracy. Users are solely responsible for ensuring the content they add complies with applicable laws and copyright terms.

---

## Features

- Single python file for the script (some people prefer to use a single file instead of having multiple files to set everything up)
- Recursively scan a provided directory for .nfo files
- Match local metadata (from NFO files) to Plex items (movies or shows) by title from NFO
- Update fields based on NFO files
- Upload poster image based on NFO filename (see requirements)
- Interactive mode available (including tab completion)
- --dry-run mode to preview changes without applying them

---

## Requirements

- Python 3.8+
- pip to install dependencies (script will attempt to auto-install missing third-party packages)
- A working Plex server with a writable token
- For posters, it is required to have the same name as the NFO files
- Running Python Script on the Plex server machine

---

## Installation

1. Clone or copy the script to a directory.
2. (Recommended) Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
3. Install dependencies (if you prefer not to rely on the script auto-installer):
```python
pip install plexapi python-dotenv
```

---

## Configuration

It is recommended, at least for Linux users, to create a .env file (<code>chmod 600</code>) in the same directory of the python script with a content like this:
```env
# Example .env
PLEX_URL=http://your-plex-host:32400
PLEX_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- <code>PLEX_URL</code>: Full base URL to your Plex server (no trailing / required). Common default: <code>http://<plex-host>:32400</code>.
- <code>PLEX_TOKEN</code>: Plex token with write permissions; ideally a server/admin token if you expect to edit metadata.
- If you do not want to use .env file, feel free to change the value <code>None</code> in the CONFIGURATIONS section for the following <code>PLEX_URL = None</code> for your Plex URL and <code>PLEX_TOKEN = None</code>.

---

## Usage

Run the script (interactive):
```bash
python3 plex-nfo-updater.py
```

Run the script (automatic):
```bash
python3 plex-nfo-updater.py --scan-path=/path/to/your/directory/to/scan
```

Show common flags:
```bash
python3 plex-nfo-updater.py --help
```

---

## Example/Sample of NFO format

### Show NFO file content:
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
	<title>Rebuild of Naruto</title>
	<originaltitle>NARUTO</originaltitle>
	<year>2002</year>
	<premiered>2002-08-03</premiered>
	<mpaa>TV-14</mpaa>
	<genre>Action / Adventure / Animation / Anime / Comedy / Drama / Fantasy</genre>
	<studio>TV Tokyo</studio>
	<rating name="" max="10">8.4</rating>
	<plot>In a world where ninja hold incredible power, the Village Hidden in the Leaves is home to some of the most skilled shinobi. Twelve years ago, a monstrous Nine-Tailed Fox attacked the village, taking many lives before it was sealed inside a newborn boy—Naruto Uzumaki. Now a mischievous ninja-in-training, Naruto dreams of becoming the greatest ninja of all time and earning the respect of everyone in the village. But his journey will be filled with trials, battles, and secrets tied to the very beast inside him.</plot>
	<namedseason number="1">Naruto</namedseason>
	<namedseason number="2">Naruto Gaiden</namedseason>
	<namedseason number="3">Kakashi Gaiden</namedseason>
	<namedseason number="4">Naruto Shippuden</namedseason>
	<namedseason number="5">Naruto Senjou</namedseason>
	<namedseason number="6">Itachi Shinden</namedseason>
	<namedseason number="7">Naruto Hiden</namedseason>
	<actor>
		<name>Junko Takeuchi</name>
		<role>Naruto Uzumaki (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/r0mRj4lNrKCmwGrzpgptKe096u1.jpg</thumb>
	</actor>
	<actor>
		<name>Noriaki Sugiyama</name>
		<role>Sasuke Uchiha (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/szqqQ8T0gzuSxjU2rnWcthsaSJT.jpg</thumb>
	</actor>
	<actor>
		<name>Chie Nakamura</name>
		<role>Sakura Haruno (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/evB6vKUbm0CKgBcgikPeFXdwd29.jpg</thumb>
	</actor>
	<actor>
		<name>Kazuhiko Inoue</name>
		<role>Kakashi Hatake (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/kRndwjOOlNi84NqIGbnitpJCQ6k.jpg</thumb>
	</actor>
	<actor>
		<name>Kouichi Touchika</name>
		<role>Neji Hyuga (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/wZYe5RmOLYIhpesKEaFIxz7YN7G.jpg</thumb>
	</actor>
	<actor>
		<name>Hidekatsu Shibata</name>
		<role>Hiruzen Sarutobi (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/hnKQe1GpuLAZY8pDnJc6eXIQzfv.jpg</thumb>
	</actor>
	<actor>
		<name>Yoichi Masukawa</name>
		<role>Rock Lee (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/sE664CcqM1pvoWsYsca7szlIzl5.jpg</thumb>
	</actor>
	<actor>
		<name>Masashi Ebara</name>
		<role>Might Guy (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/2cZRjtbA8CImvNdGk6bTP7wL2jn.jpg</thumb>
	</actor>
	<actor>
		<name>Yukari Tamura</name>
		<role>Tenten (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/a7i0z9x5HGpvPHlpV5tyryFuTHI.jpg</thumb>
	</actor>
	<actor>
		<name>Ryoka Yuzuki</name>
		<role>Ino Yamanaka (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/rizvCqUDzg6ArDBXt6Dv1eS9tIG.jpg</thumb>
	</actor>
	<actor>
		<name>Showtaro Morikubo</name>
		<role>Shikamaru Nara (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/3OsBYIbC5XBDIUVnZiDBD1dewHP.jpg</thumb>
	</actor>
	<actor>
		<name>Kentaro Ito</name>
		<role>Choji Akimichi (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/sXafSaiG99lBVV8lpkNC2naHjdR.jpg</thumb>
	</actor>
	<actor>
		<name>Shinji Kawada</name>
		<role>Shino Aburame (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/bynL2ngE9ieW8tSDRUuQM8NmRAE.jpg</thumb>
	</actor>
	<actor>
		<name>Nana Mizuki</name>
		<role>Hinata Hyuga (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/1h4C1kz8mziHmiB91MliTDHwgoh.jpg</thumb>
	</actor>
	<actor>
		<name>Kohsuke Toriumi</name>
		<role>Kiba Inuzuka (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/jsQFf7j86JF9ox2Qd3P7kvmjvmY.jpg</thumb>
	</actor>
	<actor>
		<name>Akira Ishida</name>
		<role>Gaara (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/jnW2Gn2NlR2uwOCeyOuzypnTmkH.jpg</thumb>
	</actor>
	<actor>
		<name>Toshihiko Seki</name>
		<role>Iruka Umino (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/esu8zw5fb3f7IAyQ2CDVfypbB2U.jpg</thumb>
	</actor>
	<actor>
		<name>Jurota Kosugi</name>
		<role>Asuma Sarutobi (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/em3Zh1IzkTDSdaoGBVLx89u6GuI.jpg</thumb>
	</actor>
	<actor>
		<name>Romi Park</name>
		<role>Temari (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/fEvexnzIMSiwajd7Tt1QVjSIDDS.jpg</thumb>
	</actor>
	<actor>
		<name>Nobutoshi Kanna</name>
		<role>Kabuto Yakushi (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/ijjbaeZuMuFHQJrvY0DAqzQzjht.jpg</thumb>
	</actor>
	<actor>
		<name>Kujira</name>
		<role>Orochimaru (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/dL2u3VyRBswwTEW4E8lbsHbqzeZ.jpg</thumb>
	</actor>
	<actor>
		<name>Hochu Otsuka</name>
		<role>Jiraiya (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/ouMRSpccmkS6iOMVkSc4fEOBiN2.jpg</thumb>
	</actor>
	<actor>
		<name>Ikue Otani</name>
		<role>Konohamaru Sarutobi (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/my8LBLQ4MsK4hRz1PAATIqtieaI.jpg</thumb>
	</actor>
	<actor>
		<name>Keijin Okuda</name>
		<role>Zaku Abumi (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/7VikqBtPOcEe2ETRjTRwATQlprf.jpg</thumb>
	</actor>
	<actor>
		<name>Hideo Ishikawa</name>
		<role>Itachi Uchiha (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/gEjEDNGt3CHsyzFQdNqewZVbh0.jpg</thumb>
	</actor>
	<actor>
		<name>Tomoyuki Dan</name>
		<role>Kisame Hoshigaki (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/mFCd6V5j9x6hZsepGBm1LUg9MJM.jpg</thumb>
	</actor>
	<actor>
		<name>Keiko Nemoto</name>
		<role>Shizune (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/wrcTNEmTSe3mFgykRC1xDcpwU3j.jpg</thumb>
	</actor>
	<actor>
		<name>Masako Katsuki</name>
		<role>Tsunade (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/szBdXm77jVvvHLaDoxEs9Nl9dtF.jpg</thumb>
	</actor>
	<actor>
		<name>Tesshou Genda</name>
		<role>Kyuubi (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/7eJeYv2OCHKAadeFVdabVkpWldo.jpg</thumb>
	</actor>
	<actor>
		<name>Takeshi Watabe</name>
		<role>Gamabunta (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/5H3ViQhKZFKSqCzqORDnABpa5z4.jpg</thumb>
	</actor>
	<actor>
		<name>Unsho Ishizuka</name>
		<role>Zabuza Momochi (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/jSQPB45PbMYmSFGnlX9nGM9DRr4.jpg</thumb>
	</actor>
	<actor>
		<name>Mayumi Asano</name>
		<role>Haku (voice)</role>
		<thumb>https://www.themoviedb.org/t/p/w300_and_h450_face/kn74SOAY6cfEpLkfqBBQOxsJ3LB.jpg</thumb>
	</actor>
</tvshow>
```

### Season NFO file content:
```xml
<?xml version="1.0" encoding="utf-8"?>
<seasondetails>
	<title>Naruto</title>
	<plot>Twelve years ago, a Nine-Tailed Demon Fox suddenly appeared in the Village Hidden in the Leaves. To put an end to its rampage, the village's leader, the Fourth Hokage, gave his life to seal the Nine-Tailed Fox inside a newborn child. Now, Naruto Uzumaki seeks the recognition of his peers by becoming a ninja of the Hidden Leaf Village, swearing to one day become the Hokage.</plot>
	<season>1</season>
	<episodes>17</episodes>
```
### Episode NFO file content:
```xml
<?xml version="1.0" encoding="utf-8"?>
<episodedetails>
	<originaltitle>Naruto 1a - Academy Days</originaltitle>
	<title>Academy Days</title>
	<plot>Arc 1: Childhood
A young Naruto struggles with being ostracized by the villagers, including his Academy instructor, Iruka, whose parents were killed by the Nine-Tailed Fox now within Naruto.</plot>
	<season>1</season>
	<episode>1</episode>
```
---

## References

- [Official Plex API](https://developer.plex.tv/pms/)
- [Python Plex API](https://python-plexapi.readthedocs.io/en/latest/modules/mixins.html)
