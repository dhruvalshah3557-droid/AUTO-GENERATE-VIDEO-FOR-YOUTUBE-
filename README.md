# Colour Diam Conversion Studio

Auto-generates professional branding films and ad content for
[Colour Diam](https://www.colourdiam.com).

Every video is built to convert:

1. Register — https://www.colourdiam.com/register
2. Shop — https://www.colourdiam.com/product
3. Enquire — https://www.colourdiam.com/contactus

## Beat engine

Beat tracking uses [Meteor8/beats-synced-video-generator](https://github.com/Meteor8/beats-synced-video-generator)
(librosa HPSS). Vendored in `vendor/beats-synced-video-generator`.

Extra motion template: `vendor/remotion-template`.

## Generate ads

```bash
pip3 install --break-system-packages -r requirements.txt
python3 generate.py --campaign register --format vertical
python3 generate.py --campaign shop --format vertical
python3 generate.py --campaign enquire --format vertical
python3 generate.py --campaign register --format horizontal
```

Output: `output/colourdiam_<campaign>_<format>.mp4` plus caption and YouTube copy.

## Studio

```bash
python3 app.py
```

## Auto-save to GitHub

```bash
bash scripts/save_to_github.sh "message"
```

Remote: https://github.com/dhruvalshah3557-droid/AUTO-GENERATE-VIDEO-FOR-YOUTUBE-

## Brand

- www.colourdiam.com
- +852 96440155
- Free shipping and returns, 100% money back, lifetime warranty, GIA, family since 1984
