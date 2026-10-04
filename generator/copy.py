from generator.campaigns import CAMPAIGNS


YOUTUBE_TITLES = {
    "register": [
        "Register at Colour Diam | Fancy Colour Diamonds Since 1984",
        "Members See the Colour First | www.colourdiam.com/register",
        "GIA Certified Colour Diamonds | Create Your Account Today",
    ],
    "shop": [
        "Shop Colour Diamond Jewelry | Rings, Earrings, Necklaces",
        "A Sparkle That Lasts Forever | Shop www.colourdiam.com/product",
        "Pink, Yellow and Blue Diamonds Ready to Ship",
    ],
    "enquire": [
        "Enquire With a Colour Diam Specialist | +852 96440155",
        "Custom Colour Diamond Design | www.colourdiam.com/contactus",
        "Tell Us the Colour You Cannot Forget",
    ],
}

YOUTUBE_DESCRIPTIONS = {
    "register": """Register for private diamond access.

https://www.colourdiam.com/register

Colour Diam has been a family diamond house since 1984.
GIA certified fancy colour diamonds. Free shipping. 100% money back. Lifetime warranty.

Shop: https://www.colourdiam.com/product
Enquire: https://www.colourdiam.com/contactus
Call: +852 96440155
""",
    "shop": """Shop certified colour diamond jewelry.

https://www.colourdiam.com/product

Rings. Earrings. Necklaces. Bracelets.
Certified quality. Custom designs. Exclusive offers.

Register: https://www.colourdiam.com/register
Enquire: https://www.colourdiam.com/contactus
""",
    "enquire": """Speak with a Colour Diam diamond specialist.

https://www.colourdiam.com/contactus
Call +852 96440155

Custom design. Video consultation. GIA certified. Family since 1984.

Register: https://www.colourdiam.com/register
Shop: https://www.colourdiam.com/product
""",
}


def pack_for(campaign: str) -> dict:
    data = CAMPAIGNS[campaign]
    return {
        "campaign": campaign,
        "cta": data["primary_cta"],
        "url": data["url"],
        "caption": data["caption"],
        "hashtags": data["hashtags"],
        "titles": YOUTUBE_TITLES[campaign],
        "description": YOUTUBE_DESCRIPTIONS[campaign],
    }
