CAMPAIGNS = {
    "register": {
        "goal": "Create a Colour Diam account and unlock member pricing.",
        "primary_cta": "REGISTER NOW",
        "secondary_cta": "www.colourdiam.com/register",
        "url": "https://www.colourdiam.com/register",
        "hook": "Members see the colour first.",
        "headline": "Register for private diamond access",
        "promise": "GIA certified  ·  Family since 1984",
        "trust": "Free shipping  ·  100% money back  ·  Lifetime warranty",
        "close": "Create your account. Own the sparkle.",
        "caption": (
            "Fancy colour diamonds, reserved for members.\n"
            "Register at www.colourdiam.com/register\n"
            "Free shipping. Lifetime warranty. Family since 1984."
        ),
        "hashtags": "#ColourDiam #FancyColourDiamonds #RegisterNow #GIA #LuxuryJewelry",
    },
    "shop": {
        "goal": "Drive an online purchase of jewelry or loose diamonds.",
        "primary_cta": "SHOP NOW",
        "secondary_cta": "www.colourdiam.com/product",
        "url": "https://www.colourdiam.com/product",
        "hook": "A sparkle that lasts forever.",
        "headline": "Shop certified colour diamond jewelry",
        "promise": "Rings  ·  Earrings  ·  Necklaces  ·  Bracelets",
        "trust": "Free shipping & returns  ·  Secure checkout",
        "close": "Shop now and shine bright.",
        "caption": (
            "Elegant colour diamond jewelry, ready to ship.\n"
            "Shop www.colourdiam.com/product\n"
            "Certified quality. Custom designs. Exclusive offers."
        ),
        "hashtags": "#ColourDiam #ShopDiamonds #PinkDiamond #YellowDiamond #FineJewelry",
    },
    "enquire": {
        "goal": "Capture a high-intent enquiry from a collector or gift buyer.",
        "primary_cta": "ENQUIRE NOW",
        "secondary_cta": "www.colourdiam.com/contactus",
        "url": "https://www.colourdiam.com/contactus",
        "hook": "Tell us the colour you cannot forget.",
        "headline": "Speak with a diamond specialist",
        "promise": "Personal guidance  ·  Video consultation  ·  Custom design",
        "trust": "Call +852 96440155  ·  Family since 1984",
        "close": "Enquire today. We will find your colour.",
        "caption": (
            "Looking for a rare pink, blue or yellow diamond?\n"
            "Enquire at www.colourdiam.com/contactus\n"
            "Or call +852 96440155. GIA certified. Family since 1984."
        ),
        "hashtags": "#ColourDiam #EnquireNow #CustomJewelry #GIA #ColouredDiamonds",
    },
}


def get_campaign(name: str) -> dict:
    if name not in CAMPAIGNS:
        raise ValueError(f"Unknown campaign: {name}")
    return CAMPAIGNS[name]
