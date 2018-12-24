import random
from Jumpscale import j

JSBASE = j.application.JSBaseClass


class RandomNames(j.builder._BaseClass):

    def __init__(self):
        JSBASE.__init__(self)
        self.__jslocation__ = "j.data.randomnames"


    # Names taken from moby https://raw.githubusercontent.com/moby/moby/master/pkg/namesgenerator/names-generator.go

    def hostname(self):

        left = [
         "admiring",
         "adoring",
         "affectionate",
         "agitated",
         "amazing",
         "angry",
         "awesome",
         "blissful",
         "bold",
         "boring",
         "brave",
         "charming",
         "clever",
         "cocky",
         "cool",
         "compassionate",
         "competent",
         "condescending",
         "confident",
         "cranky",
         "crazy",
         "dazzling",
         "determined",
         "distracted",
         "dreamy",
         "eager",
         "ecstatic",
         "elastic",
         "elated",
         "elegant",
         "eloquent",
         "epic",
         "fervent",
         "festive",
         "flamboyant",
         "focused",
         "friendly",
         "frosty",
         "gallant",
         "gifted",
         "goofy",
         "gracious",
         "happy",
         "hardcore",
         "heuristic",
         "hopeful",
         "hungry",
         "infallible",
         "inspiring",
         "jolly",
         "jovial",
         "keen",
         "kind",
         "laughing",
         "loving",
         "lucid",
         "magical",
         "mystifying",
         "modest",
         "musing",
         "naughty",
         "nervous",
         "nifty",
         "nostalgic",
         "objective",
         "optimistic",
         "peaceful",
         "pedantic",
         "pensive",
         "practical",
         "priceless",
         "quirky",
         "quizzical",
         "recursing",
         "relaxed",
         "reverent",
         "romantic",
         "sad",
         "serene",
         "sharp",
         "silly",
         "sleepy",
         "stoic",
         "stupefied",
         "suspicious",
         "sweet",
         "tender",
         "thirsty",
         "trusting",
         "unruffled",
         "upbeat",
         "vibrant",
         "vigilant",
         "vigorous",
         "wizardly",
         "wonderful",
         "xenodochial",
         "youthful",
         "zealous",
         "zen",
        ]



        right = ["albattani",
        "allen",
        "almeida",
        "antonelli",
        "agnesi",
        "archimedes",
        "ardinghelli",
        "aryabhata",
        "austin",
        "babbage",
        "banach",
        "banzai",
        "bardeen",
        "bartik",
        "bassi",
        "beaver",
        "bell",
        "benz",
        "bhabha",
        "bhaskara",
        "black",
        "blackburn",
        "blackwell",
        "bohr",
        "booth",
        "borg",
        "bose",
        "boyd",
        "brahmagupta",
        "brattain",
        "brown",
        "burnell",
        "buck",
        "burnell",
        "cannon",
        "carson",
        "cartwright",
        "chandrasekhar",
        "chaplygin",
        "chatelet",
        "chatterjee",
        "chebyshev",
        "cocks",
        "cohen",
        "chaum",
        "clarke",
        "colden",
        "cori",
        "cray",
        "wiles",
        "williams",
        "williamson",
        "wilson",
        "wing",
        "wozniak",
        "wright",
        "wu",
        "yalow",
        "yonath",
        "zhukovsky",
        ]

        random_left = random.choice(left)
        random_right = random.choice(right)
        return "{}_{}".format(random_left, random_right)
