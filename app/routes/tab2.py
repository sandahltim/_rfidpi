from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
import sqlite3

tab2_bp = Blueprint("tab2_bp", __name__, url_prefix="/tab2")

# Hardcoded mappings from seed data
CATEGORY_MAP = {
    # Tent Tops
    66456: 'Tent Tops',  # HP 15x15 IKEs Bar
    4203: 'Tent Tops',   # TOP NAVI LITE 30x15 HIP G1
    4204: 'Tent Tops',   # TOP NAVI LITE 30x15 MID G1
    72392: 'Tent Tops',  # TOP NAVI LITE 30x15 HIP G2
    66324: 'Tent Tops',  # TOP NAVI LITE 30x15 MID G2
    72401: 'Tent Tops',  # CRATE, HP 10 x 10 ASSEMBLY
    72402: 'Tent Tops',  # CRATE, HP 15 x 15 ASSEMBLY
    72403: 'Tent Tops',  # CRATE, HP 10 x 20 ASSEMBLY
    72405: 'Tent Tops',  # CRATE, HP 30 x 30 ASSEMBLY
    72404: 'Tent Tops',  # CRATE, HP 20 x 20 ASSEMBLY
    72407: 'Tent Tops',  # CRATE, HP 20 x 30 ASSEMBLY
    72408: 'Tent Tops',  # CRATE, NAVI HIP ASSEMBLY
    72409: 'Tent Tops',  # CRATE, NAVI MID ASSEMBLY
    72412: 'Tent Tops',  # CRATE, NAVI INSTALLATION
    72410: 'Tent Tops',  # CRATE, NAVI LITE HIP ASSEMBLY
    72411: 'Tent Tops',  # CRATE, NAVI LITE MID ASSEMBLY
    72406: 'Tent Tops',  # CRATE, HP HEX 35 x 40 ASSEMBLY
    72252: 'Tent Tops',  # SIDEWALL KEDAR -G 8' x 5' PANEL
    72253: 'Tent Tops',  # SIDEWALL KEDAR -R 8' x 5' PANEL

    # Tables and Chairs
    63131: 'Tables and Chairs',  # TOP, TABLE ROUND, 30 INCH PLYWOOD
    65722: 'Tables and Chairs',  # TOP, TABLE ROUND, 36 INCH PLYWOOD
    66554: 'Tables and Chairs',  # LEG BASE 24 - 4 PRONG X
    66555: 'Tables and Chairs',  # LEG BASE 30 - 4 PRONG X FOR 36R

    # Round Linen
    61885: 'Round Linen',  # 108 ROUND WHITE LINEN
    61914: 'Round Linen',  # 108 ROUND AMETHYST LINEN
    61890: 'Round Linen',  # 108 ROUND BEIGE LINEN
    61886: 'Round Linen',  # 108 ROUND BLACK LINEN
    61908: 'Round Linen',  # 108 ROUND BURGUNDY LINEN
    61901: 'Round Linen',  # 108 ROUND CARDINAL RED LINEN
    61925: 'Round Linen',  # 108 ROUND CELADON (SAGE) LINEN
    61891: 'Round Linen',  # 108 ROUND CHOCOLATE LINEN
    61912: 'Round Linen',  # 108 ROUND EGGPLANT LINEN
    61910: 'Round Linen',  # 108 ROUND GRAPE (PURPLE) LINEN
    61887: 'Round Linen',  # 108 ROUND GREY LINEN
    61889: 'Round Linen',  # 108 ROUND IVORY LINEN
    61893: 'Round Linen',  # 108 ROUND MAIZE LINEN
    61904: 'Round Linen',  # 108 ROUND PASTEL PINK LINEN
    61896: 'Round Linen',  # 108 ROUND PEACH LINEN
    61888: 'Round Linen',  # 108 ROUND PEWTER LINEN
    61905: 'Round Linen',  # 108 ROUND PINK LINEN
    61895: 'Round Linen',  # 108 ROUND POPPY LINEN
    61979: 'Round Linen',  # 120 ROUND WHITE NOVA SWIRL LINEN
    61958: 'Round Linen',  # 120 ROUND AMETHYST LINEN
    61978: 'Round Linen',  # 120 ROUND APPLE GREEN NOVA SOLID
    61934: 'Round Linen',  # 120 ROUND BEIGE LINEN
    61977: 'Round Linen',  # 120 ROUND BERMUDA BLUE NOVA SOLID
    61953: 'Round Linen',  # 120 ROUND BURGUNDY LINEN
    61939: 'Round Linen',  # 120 ROUND BYZANTINE FALL GOLD LIN
    61946: 'Round Linen',  # 120 ROUND CARDINAL RED LINEN
    61936: 'Round Linen',  # 120 ROUND CHOCOLATE LINEN
    61973: 'Round Linen',  # 120 ROUND DAMASK SOMERSET GOLD LI
    61957: 'Round Linen',  # 120 ROUND EGGPLANT LINEN
    61976: 'Round Linen',  # 120 ROUND FUCHSIA NOVA SOLID LINE
    61955: 'Round Linen',  # 120 ROUND GRAPE LINEN
    61970: 'Round Linen',  # 120 ROUND HUNTER GREEN LINEN
    61933: 'Round Linen',  # 120 ROUND IVORY LINEN
    61971: 'Round Linen',  # 120 ROUND KELLY GREEN LINEN
    61937: 'Round Linen',  # 120 ROUND LEMON YELLOW LINEN
    61961: 'Round Linen',  # 120 ROUND LIGHT BLUE LINEN
    61972: 'Round Linen',  # 120 ROUND LIME GREEN LINEN
    61951: 'Round Linen',  # 120 ROUND MAGENTA LINEN
    61975: 'Round Linen',  # 120 ROUND MIDNIGHT BLUE IRIDESCEN
    61962: 'Round Linen',  # 120 ROUND MINT LINEN
    61968: 'Round Linen',  # 120 ROUND NAVY BLUE LINEN
    61965: 'Round Linen',  # 120 ROUND OCEAN BLUE LINEN
    61942: 'Round Linen',  # 120 ROUND ORANGE LINEN
    61949: 'Round Linen',  # 120 ROUND PASTEL PINK LINEN
    61967: 'Round Linen',  # 120 ROUND PERIWINKLE LINEN
    61950: 'Round Linen',  # 120 ROUND PINK LINEN
    61974: 'Round Linen',  # 120 ROUND ROSE IRIDESCENT CRUSH L
    61960: 'Round Linen',  # 120 ROUND ROYAL BLUE LINEN
    61943: 'Round Linen',  # 120 ROUND SHRIMP LINEN
    61964: 'Round Linen',  # 120 ROUND TURQUOISE LINEN
    72485: 'Round Linen',  # 120 ROUND DUSTY ROSE
    61981: 'Round Linen',  # 132 ROUND WHITE LINEN
    62032: 'Round Linen',  # 132 ROUND WHITE SAND IRIDESCENT
    62012: 'Round Linen',  # 132 ROUND AMETHYST LINEN
    62028: 'Round Linen',  # 132 ROUND ARMY GREEN LINEN
    61986: 'Round Linen',  # 132 ROUND BEIGE LINEN
    61982: 'Round Linen',  # 132 ROUND BLACK LINEN
    61996: 'Round Linen',  # 132 ROUND BUBBLEGUM PINK LINEN
    62006: 'Round Linen',  # 132 ROUND BURGUNDY LINEN
    62027: 'Round Linen',  # 132 ROUND BURNT ORANGE LINEN
    61999: 'Round Linen',  # 132 ROUND CARDINAL RED LINEN
    62031: 'Round Linen',  # 132 ROUND CHAMPAGNE IRIDESCENT CR
    62030: 'Round Linen',  # 132 ROUND DAMASK CAMBRIDGE WHEAT
    62029: 'Round Linen',  # 132 ROUND DAMASK SOMERSET GOLD
    62010: 'Round Linen',  # 132 ROUND EGGPLANT LINEN
    62024: 'Round Linen',  # 132 ROUND HUNTER GREEN LINEN
    61985: 'Round Linen',  # 132 ROUND IVORY LINEN
    62025: 'Round Linen',  # 132 ROUND KELLY GREEN LINEN
    61989: 'Round Linen',  # 132 ROUND LEMON YELLOW LINEN
    62026: 'Round Linen',  # 132 ROUND LIME GREEN LINEN
    62004: 'Round Linen',  # 132 ROUND MAGENTA LINEN
    62034: 'Round Linen',  # 132 ROUND MIDNIGHT BLUE IRIDESCEN
    62022: 'Round Linen',  # 132 ROUND NAVY BLUE LINEN
    61994: 'Round Linen',  # 132 ROUND ORANGE LINEN
    62021: 'Round Linen',  # 132 ROUND PERIWINKLE LINEN
    61984: 'Round Linen',  # 132 ROUND PEWTER LINEN
    62003: 'Round Linen',  # 132 ROUND PINK LINEN
    61992: 'Round Linen',  # 132 ROUND POPPY LINEN
    62014: 'Round Linen',  # 132 ROUND ROYAL BLUE LINEN
    62033: 'Round Linen',  # 132 ROUND SUNSET ORANGE IRD CRUSH
    62035: 'Round Linen',  # 132 ROUND TIFFANY BLUE NOVA SOLID

    # Rectangle Linen
    62287: 'Rectangle Linen',  # 30X96 CONFERENCE LINEN WHITE
    62288: 'Rectangle Linen',  # 30X96 CONFERENCE LINEN BLACK
    62289: 'Rectangle Linen',  # 30X96 CONFERENCE LINEN EGGPLANT
    62291: 'Rectangle Linen',  # 54 SQUARE WHITE LINEN
    62321: 'Rectangle Linen',  # 54 SQUARE AMETHYST LINEN
    62336: 'Rectangle Linen',  # 54 SQUARE ARMY GREEN LINEN
    62292: 'Rectangle Linen',  # 54 SQUARE BLACK LINEN
    62315: 'Rectangle Linen',  # 54 SQUARE BURGUNDY LINEN
    62337: 'Rectangle Linen',  # 54 SQUARE BURLAP (PRAIRIE) LINEN
    62332: 'Rectangle Linen',  # 54 SQUARE CELADON LINEN
    62298: 'Rectangle Linen',  # 54 SQUARE CHOCOLATE LINEN
    62319: 'Rectangle Linen',  # 54 SQUARE EGGPLANT LINEN
    62333: 'Rectangle Linen',  # 54 SQUARE HUNTER GREEN LINEN
    62295: 'Rectangle Linen',  # 54 SQUARE IVORY LINEN
    62331: 'Rectangle Linen',  # 54 SQUARE NAVY BLUE LINEN
    62330: 'Rectangle Linen',  # 54 SQUARE PERIWINKLE LINEN
    62294: 'Rectangle Linen',  # 54 SQUARE PEWTER LINEN
    62312: 'Rectangle Linen',  # 54 SQUARE PINK LINEN
    62323: 'Rectangle Linen',  # 54 SQUARE ROYAL BLUE LINEN
    62338: 'Rectangle Linen',  # 54 SQUARE SILVER LAME LINEN
    62339: 'Rectangle Linen',  # 72 SQUARE BURLAP (PRAIRIE) LINEN
    62088: 'Rectangle Linen',  # 60X120 WHITE LINEN
    62119: 'Rectangle Linen',  # 60X120 AMETHYST LINEN
    62093: 'Rectangle Linen',  # 60X120 BEIGE LINEN
    62089: 'Rectangle Linen',  # 60X120 BLACK LINEN
    62103: 'Rectangle Linen',  # 60X120 BUBBLEGUM PINK LINEN
    62114: 'Rectangle Linen',  # 60X120 BURGUNDY LINEN
    62098: 'Rectangle Linen',  # 60X120 BYZANTINE FALL GOLD LINEN
    62106: 'Rectangle Linen',  # 60X120 CARDINAL RED LINEN
    62130: 'Rectangle Linen',  # 60X120 CELADON LINEN
    62095: 'Rectangle Linen',  # 60X120 CHOCOLATE LINEN
    62118: 'Rectangle Linen',  # 60X120 EGGPLANT LINEN
    62113: 'Rectangle Linen',  # 60X120 FLAMINGO LINEN
    62116: 'Rectangle Linen',  # 60X120 GRAPE LINEN
    62090: 'Rectangle Linen',  # 60X120 GREY LINEN
    62107: 'Rectangle Linen',  # 60X120 HOT PINK LINEN
    62131: 'Rectangle Linen',  # 60X120 HUNTER GREEN LINEN
    62092: 'Rectangle Linen',  # 60X120 IVORY LINEN
    62132: 'Rectangle Linen',  # 60X120 KELLY GREEN LINEN
    62094: 'Rectangle Linen',  # 60X120 KHAKI LINEN
    62096: 'Rectangle Linen',  # 60X120 LEMON YELLOW LINEN
    62122: 'Rectangle Linen',  # 60X120 LIGHT BLUE LINEN
    62133: 'Rectangle Linen',  # 60X120 LIME GREEN LINEN
    62112: 'Rectangle Linen',  # 60X120 MAGENTA LINEN
    62129: 'Rectangle Linen',  # 60X120 NAVY BLUE LINEN
    62126: 'Rectangle Linen',  # 60X120 OCEAN BLUE LINEN
    62101: 'Rectangle Linen',  # 60X120 ORANGE LINEN
    62091: 'Rectangle Linen',  # 60X120 PEWTER LINEN
    62111: 'Rectangle Linen',  # 60X120 PINK LINEN
    62117: 'Rectangle Linen',  # 60X120 PLUM LINEN
    62099: 'Rectangle Linen',  # 60X120 POPPY LINEN
    62104: 'Rectangle Linen',  # 60X120 RED LINEN
    62136: 'Rectangle Linen',  # 60X120 ROSE IRIDESCENT CRUSH LINEN
    62121: 'Rectangle Linen',  # 60X120 ROYAL BLUE LINEN
    62102: 'Rectangle Linen',  # 60X120 SHRIMP LINEN
    62142: 'Rectangle Linen',  # 60X120 SILVER LAME
    62139: 'Rectangle Linen',  # 60X120 SOFT SAGE NOVA SOLID LINEN
    62138: 'Rectangle Linen',  # 60X120 TIFFANY BLUE NOVA SOLID LIN
    62137: 'Rectangle Linen',  # 60X120 VIOLET GREEN IRIDESCENT CRU
    62187: 'Rectangle Linen',  # 90X132 WHITE LINEN ROUNDED CORNE
    62211: 'Rectangle Linen',  # 90X132 BURGUNDY LINEN ROUNDED COR
    62191: 'Rectangle Linen',  # 90X132 IVORY LINEN ROUNDED CORNER
    62227: 'Rectangle Linen',  # 90X132 NAVY BLUE LINEN ROUNDED CO
    62224: 'Rectangle Linen',  # 90X132 OCEAN LINEN ROUNDED CORNER
    62225: 'Rectangle Linen',  # 90X132 PACIFICA LINEN ROUNDED COR
    62226: 'Rectangle Linen',  # 90X132 PERIWINKLE LINEN ROUNDED C
    62214: 'Rectangle Linen',  # 90X132 PLUM LINEN ROUNDED CORNERS
    62198: 'Rectangle Linen',  # 90X132 POPPY LINEN ROUNDED CORNER
    62219: 'Rectangle Linen',  # 90X132 ROYAL BLUE LINEN ROUNDED C
    62235: 'Rectangle Linen',  # 90X156 WHITE LINEN ROUNDED CORNE
    62265: 'Rectangle Linen',  # 90X156 AMETHYST LINEN ROUNDED COR
    62236: 'Rectangle Linen',  # 90X156 BLACK LINEN ROUNDED CORNER
    62252: 'Rectangle Linen',  # 90X156 CARDINAL RED LINEN ROUNDED
    62242: 'Rectangle Linen',  # 90X156 CHOCOLATE LINEN ROUNDED CO
    62280: 'Rectangle Linen',  # 90X156 DAMASK SOMERSET GOLD LINEN
    62263: 'Rectangle Linen',  # 90X156 EGGPLANT LINEN ROUNDED COR
    62237: 'Rectangle Linen',  # 90X156 GREY LINEN ROUNDED CORNERS
    62277: 'Rectangle Linen',  # 90X156 HUNTER GREEN LINEN ROUNDED
    62239: 'Rectangle Linen',  # 90X156 IVORY LINEN ROUNDED CORNER
    62268: 'Rectangle Linen',  # 90X156 LIGHT BLUE LINEN ROUNDED C
    62257: 'Rectangle Linen',  # 90X156 MAGENTA LINEN ROUNDED CORN
    62275: 'Rectangle Linen',  # 90X156 NAVY BLUE LINEN ROUNDED CO
    62272: 'Rectangle Linen',  # 90X156 OCEAN LINEN ROUNDED CORNER
    62273: 'Rectangle Linen',  # 90X156 PACIFICA LINEN ROUNDED COR
    62255: 'Rectangle Linen',  # 90X156 PASTEL PINK LINEN ROUNDED
    62247: 'Rectangle Linen',  # 90X156 PEACH LINEN ROUNDED CORNER
    62274: 'Rectangle Linen',  # 90X156 PERIWINKLE LINEN ROUNDED C
    62238: 'Rectangle Linen',  # 90X156 PEWTER LINEN ROUNDED CORNE
    62256: 'Rectangle Linen',  # 90X156 PINK LINEN ROUNDED CORNERS
    62246: 'Rectangle Linen',  # 90X156 POPPY LINEN ROUNDED CORNER
    62267: 'Rectangle Linen',  # 90X156 ROYAL BLUE LINEN ROUNDED C
    62271: 'Rectangle Linen',  # 90X156 TURQUOISE LINEN ROUNDED CO

    # Concession
    62468: 'Concession',  # BEVERAGE COOLER, 10 GAL CAMBRO THERMOVAT
    3290: 'Concession',   # BEVERAGE COOLER, 5 GAL CAMBRO THERMOVAT
    62479: 'Concession',  # BEVERAGE DISPENSER, CLEAR 5 GAL w/INFUSE
    62475: 'Concession',  # BEVERAGE DISPENSER, CLEAR-IVORY 5 GAL
    62636: 'Concession',  # CHAFER, FULLSIZE, ROLLTOP, STAINLESS 8QT
    62633: 'Concession',  # CHAFER, FULLSIZE, STAINLESS (GOLD TRIM)
    62634: 'Concession',  # CHAFER, FULLSIZE, STAINLESS STEEL
    62637: 'Concession',  # CHAFER, HALFSIZE, STAINLESS STEEL
    62654: 'Concession',  # FOUNTAIN, 3 GAL EMPRESS (6 AMP)
    62651: 'Concession',  # FOUNTAIN, 3 GAL PRINCESS (6AMP)
    62653: 'Concession',  # FOUNTAIN, 4 1/2 GAL EMPRESS (6 AMP)
    62652: 'Concession'   # FOUNTAIN, 7 GAL PRINCESS (6 AMP)
}

SUBCATEGORY_MAP = {
    # Tent Tops
    66456: 'HP Tents',    # HP 15x15 IKEs Bar
    4203: 'Navi Tents',   # TOP NAVI LITE 30x15 HIP G1
    4204: 'Navi Tents',   # TOP NAVI LITE 30x15 MID G1
    72392: 'Navi Tents',  # TOP NAVI LITE 30x15 HIP G2
    66324: 'Navi Tents',  # TOP NAVI LITE 30x15 MID G2
    72401: 'HP Tents',    # CRATE, HP 10 x 10 ASSEMBLY
    72402: 'HP Tents',    # CRATE, HP 15 x 15 ASSEMBLY
    72403: 'HP Tents',    # CRATE, HP 10 x 20 ASSEMBLY
    72405: 'HP Tents',    # CRATE, HP 30 x 30 ASSEMBLY
    72404: 'HP Tents',    # CRATE, HP 20 x 20 ASSEMBLY
    72407: 'HP Tents',    # CRATE, HP 20 x 30 ASSEMBLY
    72408: 'Navi Tents',  # CRATE, NAVI HIP ASSEMBLY
    72409: 'Navi Tents',  # CRATE, NAVI MID ASSEMBLY
    72412: 'Navi Tents',  # CRATE, NAVI INSTALLATION
    72410: 'Navi Tents',  # CRATE, NAVI LITE HIP ASSEMBLY
    72411: 'Navi Tents',  # CRATE, NAVI LITE MID ASSEMBLY
    72406: 'HP Tents',    # CRATE, HP HEX 35 x 40 ASSEMBLY
    72252: 'Other Tents', # SIDEWALL KEDAR -G 8' x 5' PANEL
    72253: 'Other Tents', # SIDEWALL KEDAR -R 8' x 5' PANEL

    # Tables and Chairs
    63131: 'Tables',  # TOP, TABLE ROUND, 30 INCH PLYWOOD
    65722: 'Tables',  # TOP, TABLE ROUND, 36 INCH PLYWOOD
    66554: 'Chairs',  # LEG BASE 24 - 4 PRONG X
    66555: 'Chairs',  # LEG BASE 30 - 4 PRONG X FOR 36R

    # Round Linen
    61885: '108-inch Round',  # 108 ROUND WHITE LINEN
    61914: '108-inch Round',  # 108 ROUND AMETHYST LINEN
    61890: '108-inch Round',  # 108 ROUND BEIGE LINEN
    61886: '108-inch Round',  # 108 ROUND BLACK LINEN
    61908: '108-inch Round',  # 108 ROUND BURGUNDY LINEN
    61901: '108-inch Round',  # 108 ROUND CARDINAL RED LINEN
    61925: '108-inch Round',  # 108 ROUND CELADON (SAGE) LINEN
    61891: '108-inch Round',  # 108 ROUND CHOCOLATE LINEN
    61912: '108-inch Round',  # 108 ROUND EGGPLANT LINEN
    61910: '108-inch Round',  # 108 ROUND GRAPE (PURPLE) LINEN
    61887: '108-inch Round',  # 108 ROUND GREY LINEN
    61889: '108-inch Round',  # 108 ROUND IVORY LINEN
    61893: '108-inch Round',  # 108 ROUND MAIZE LINEN
    61904: '108-inch Round',  # 108 ROUND PASTEL PINK LINEN
    61896: '108-inch Round',  # 108 ROUND PEACH LINEN
    61888: '108-inch Round',  # 108 ROUND PEWTER LINEN
    61905: '108-inch Round',  # 108 ROUND PINK LINEN
    61895: '108-inch Round',  # 108 ROUND POPPY LINEN
    61979: '120-inch Round',  # 120 ROUND WHITE NOVA SWIRL LINEN
    61958: '120-inch Round',  # 120 ROUND AMETHYST LINEN
    61978: '120-inch Round',  # 120 ROUND APPLE GREEN NOVA SOLID
    61934: '120-inch Round',  # 120 ROUND BEIGE LINEN
    61977: '120-inch Round',  # 120 ROUND BERMUDA BLUE NOVA SOLID
    61953: '120-inch Round',  # 120 ROUND BURGUNDY LINEN
    61939: '120-inch Round',  # 120 ROUND BYZANTINE FALL GOLD LIN
    61946: '120-inch Round',  # 120 ROUND CARDINAL RED LINEN
    61936: '120-inch Round',  # 120 ROUND CHOCOLATE LINEN
    61973: '120-inch Round',  # 120 ROUND DAMASK SOMERSET GOLD LI
    61957: '120-inch Round',  # 120 ROUND EGGPLANT LINEN
    61976: '120-inch Round',  # 120 ROUND FUCHSIA NOVA SOLID LINE
    61955: '120-inch Round',  # 120 ROUND GRAPE LINEN
    61970: '120-inch Round',  # 120 ROUND HUNTER GREEN LINEN
    61933: '120-inch Round',  # 120 ROUND IVORY LINEN
    61971: '120-inch Round',  # 120 ROUND KELLY GREEN LINEN
    61937: '120-inch Round',  # 120 ROUND LEMON YELLOW LINEN
    61961: '120-inch Round',  # 120 ROUND LIGHT BLUE LINEN
    61972: '120-inch Round',  # 120 ROUND LIME GREEN LINEN
    61951: '120-inch Round',  # 120 ROUND MAGENTA LINEN
    61975: '120-inch Round',  # 120 ROUND MIDNIGHT BLUE IRIDESCEN
    61962: '120-inch Round',  # 120 ROUND MINT LINEN
    61968: '120-inch Round',  # 120 ROUND NAVY BLUE LINEN
    61965: '120-inch Round',  # 120 ROUND OCEAN BLUE LINEN
    61942: '120-inch Round',  # 120 ROUND ORANGE LINEN
    61949: '120-inch Round',  # 120 ROUND PASTEL PINK LINEN
    61967: '120-inch Round',  # 120 ROUND PERIWINKLE LINEN
    61950: '120-inch Round',  # 120 ROUND PINK LINEN
    61974: '120-inch Round',  # 120 ROUND ROSE IRIDESCENT CRUSH L
    61960: '120-inch Round',  # 120 ROUND ROYAL BLUE LINEN
    61943: '120-inch Round',  # 120 ROUND SHRIMP LINEN
    61964: '120-inch Round',  # 120 ROUND TURQUOISE LINEN
    72485: '120-inch Round',  # 120 ROUND DUSTY ROSE
    61981: '132-inch Round',  # 132 ROUND WHITE LINEN
    62032: '132-inch Round',  # 132 ROUND WHITE SAND IRIDESCENT
    62012: '132-inch Round',  # 132 ROUND AMETHYST LINEN
    62028: '132-inch Round',  # 132 ROUND ARMY GREEN LINEN
    61986: '132-inch Round',  # 132 ROUND BEIGE LINEN
    61982: '132-inch Round',  # 132 ROUND BLACK LINEN
    61996: '132-inch Round',  # 132 ROUND BUBBLEGUM PINK LINEN
    62006: '132-inch Round',  # 132 ROUND BURGUNDY LINEN
    62027: '132-inch Round',  # 132 ROUND BURNT ORANGE LINEN
    61999: '132-inch Round',  # 132 ROUND CARDINAL RED LINEN
    62031: '132-inch Round',  # 132 ROUND CHAMPAGNE IRIDESCENT CR
    62030: '132-inch Round',  # 132 ROUND DAMASK CAMBRIDGE WHEAT
    62029: '132-inch Round',  # 132 ROUND DAMASK SOMERSET GOLD
    62010: '132-inch Round',  # 132 ROUND EGGPLANT LINEN
    62024: '132-inch Round',  # 132 ROUND HUNTER GREEN LINEN
    61985: '132-inch Round',  # 132 ROUND IVORY LINEN
    62025: '132-inch Round',  # 132 ROUND KELLY GREEN LINEN
    61989: '132-inch Round',  # 132 ROUND LEMON YELLOW LINEN
    62026: '132-inch Round',  # 132 ROUND LIME GREEN LINEN
    62004: '132-inch Round',  # 132 ROUND MAGENTA LINEN
    62034: '132-inch Round',  # 132 ROUND MIDNIGHT BLUE IRIDESCEN
    62022: '132-inch Round',  # 132 ROUND NAVY BLUE LINEN
    61994: '132-inch Round',  # 132 ROUND ORANGE LINEN
    62021: '132-inch Round',  # 132 ROUND PERIWINKLE LINEN
    61984: '132-inch Round',  # 132 ROUND PEWTER LINEN
    62003: '132-inch Round',  # 132 ROUND PINK LINEN
    61992: '132-inch Round',  # 132 ROUND POPPY LINEN
    62014: '132-inch Round',  # 132 ROUND ROYAL BLUE LINEN
    62033: '132-inch Round',  # 132 ROUND SUNSET ORANGE IRD CRUSH
    62035: '132-inch Round',  # 132 ROUND TIFFANY BLUE NOVA SOLID

    # Rectangle Linen
    62287: 'Other Rectangle Linen',  # 30X96 CONFERENCE LINEN WHITE
    62288: 'Other Rectangle Linen',  # 30X96 CONFERENCE LINEN BLACK
    62289: 'Other Rectangle Linen',  # 30X96 CONFERENCE LINEN EGGPLANT
    62291: '54 Square',  # 54 SQUARE WHITE LINEN
    62321: '54 Square',  # 54 SQUARE AMETHYST LINEN
    62336: '54 Square',  # 54 SQUARE ARMY GREEN LINEN
    62292: '54 Square',  # 54 SQUARE BLACK LINEN
    62315: '54 Square',  # 54 SQUARE BURGUNDY LINEN
    62337: '54 Square',  # 54 SQUARE BURLAP (PRAIRIE) LINEN
    62332: '54 Square',  # 54 SQUARE CELADON LINEN
    62298: '54 Square',  # 54 SQUARE CHOCOLATE LINEN
    62319: '54 Square',  # 54 SQUARE EGGPLANT LINEN
    62333: '54 Square',  # 54 SQUARE HUNTER GREEN LINEN
    62295: '54 Square',  # 54 SQUARE IVORY LINEN
    62331: '54 Square',  # 54 SQUARE NAVY BLUE LINEN
    62330: '54 Square',  # 54 SQUARE PERIWINKLE LINEN
    62294: '54 Square',  # 54 SQUARE PEWTER LINEN
    62312: '54 Square',  # 54 SQUARE PINK LINEN
    62323: '54 Square',  # 54 SQUARE ROYAL BLUE LINEN
    62338: '54 Square',  # 54 SQUARE SILVER LAME LINEN
    62339: 'Other Rectangle Linen',  # 72 SQUARE BURLAP (PRAIRIE) LINEN
    62088: '60x120',  # 60X120 WHITE LINEN
    62119: '60x120',  # 60X120 AMETHYST LINEN
    62093: '60x120',  # 60X120 BEIGE LINEN
    62089: '60x120',  # 60X120 BLACK LINEN
    62103: '60x120',  # 60X120 BUBBLEGUM PINK LINEN
    62114: '60x120',  # 60X120 BURGUNDY LINEN
    62098: '60x120',  # 60X120 BYZANTINE FALL GOLD LINEN
    62106: '60x120',  # 60X120 CARDINAL RED LINEN
    62130: '60x120',  # 60X120 CELADON LINEN
    62095: '60x120',  # 60X120 CHOCOLATE LINEN
    62118: '60x120',  # 60X120 EGGPLANT LINEN
    62113: '60x120',  # 60X120 FLAMINGO LINEN
    62116: '60x120',  # 60X120 GRAPE LINEN
    62090: '60x120',  # 60X120 GREY LINEN
    62107: '60x120',  # 60X120 HOT PINK LINEN
    62131: '60x120',  # 60X120 HUNTER GREEN LINEN
    62092: '60x120',  # 60X120 IVORY LINEN
    62132: '60x120',  # 60X120 KELLY GREEN LINEN
    62094: '60x120',  # 60X120 KHAKI LINEN
    62096: '60x120',  # 60X120 LEMON YELLOW LINEN
    62122: '60x120',  # 60X120 LIGHT BLUE LINEN
    62133: '60x120',  # 60X120 LIME GREEN LINEN
    62112: '60x120',  # 60X120 MAGENTA LINEN
    62129: '60x120',  # 60X120 NAVY BLUE LINEN
    62126: '60x120',  # 60X120 OCEAN BLUE LINEN
    62101: '60x120',  # 60X120 ORANGE LINEN
    62091: '60x120',  # 60X120 PEWTER LINEN
    62111: '60x120',  # 60X120 PINK LINEN
    62117: '60x120',  # 60X120 PLUM LINEN
    62099: '60x120',  # 60X120 POPPY LINEN
    62104: '60x120',  # 60X120 RED LINEN
    62136: '60x120',  # 60X120 ROSE IRIDESCENT CRUSH LINEN
    62121: '60x120',  # 60X120 ROYAL BLUE LINEN
    62102: '60x120',  # 60X120 SHRIMP LINEN
    62142: '60x120',  # 60X120 SILVER LAME
    62139: '60x120',  # 60X120 SOFT SAGE NOVA SOLID LINEN
    62138: '60x120',  # 60X120 TIFFANY BLUE NOVA SOLID LIN
    62137: '60x120',  # 60X120 VIOLET GREEN IRIDESCENT CRU
    62187: '90x132',  # 90X132 WHITE LINEN ROUNDED CORNE
    62211: '90x132',  # 90X132 BURGUNDY LINEN ROUNDED COR
    62191: '90x132',  # 90X132 IVORY LINEN ROUNDED CORNER
    62227: '90x132',  # 90X132 NAVY BLUE LINEN ROUNDED CO
    62224: '90x132',  # 90X132 OCEAN LINEN ROUNDED CORNER
    62225: '90x132',  # 90X132 PACIFICA LINEN ROUNDED COR
    62226: '90x132',  # 90X132 PERIWINKLE LINEN ROUNDED C
    62214: '90x132',  # 90X132 PLUM LINEN ROUNDED CORNERS
    62198: '90x132',  # 90X132 POPPY LINEN ROUNDED CORNER
    62219: '90x132',  # 90X132 ROYAL BLUE LINEN ROUNDED C
    62235: '90x156',  # 90X156 WHITE LINEN ROUNDED CORNE
    62265: '90x156',  # 90X156 AMETHYST LINEN ROUNDED COR
    62236: '90x156',  # 90X156 BLACK LINEN ROUNDED CORNER
    62252: '90x156',  # 90X156 CARDINAL RED LINEN ROUNDED
    62242: '90x156',  # 90X156 CHOCOLATE LINEN ROUNDED CO
    62280: '90x156',  # 90X156 DAMASK SOMERSET GOLD LINEN
    62263: '90x156',  # 90X156 EGGPLANT LINEN ROUNDED COR
    62237: '90x156',  # 90X156 GREY LINEN ROUNDED CORNERS
    62277: '90x156',  # 90X156 HUNTER GREEN LINEN ROUNDED
    62239: '90x156',  # 90X156 IVORY LINEN ROUNDED CORNER
    62268: '90x156',  # 90X156 LIGHT BLUE LINEN ROUNDED C
    62257: '90x156',  # 90X156 MAGENTA LINEN ROUNDED CORN
    62275: '90x156',  # 90X156 NAVY BLUE LINEN ROUNDED CO
    62272: '90x156',  # 90X156 OCEAN LINEN ROUNDED CORNER
    62273: '90x156',  # 90X156 PACIFICA LINEN ROUNDED COR
    62255: '90x156',  # 90X156 PASTEL PINK LINEN ROUNDED
    62247: '90x156',  # 90X156 PEACH LINEN ROUNDED CORNER
    62274: '90x156',  # 90X156 PERIWINKLE LINEN ROUNDED C
    62238: '90x156',  # 90X156 PEWTER LINEN ROUNDED CORNE
    62256: '90x156',  # 90X156 PINK LINEN ROUNDED CORNERS
    62246: '90x156',  # 90X156 POPPY LINEN ROUNDED CORNER
    62267: '90x156',  # 90X156 ROYAL BLUE LINEN ROUNDED C
    62271: '90x156',  # 90X156 TURQUOISE LINEN ROUNDED CO

    # Concession
    62468: 'Equipment',  # BEVERAGE COOLER, 10 GAL CAMBRO THERMOVAT
    3290: 'Equipment',   # BEVERAGE COOLER, 5 GAL CAMBRO THERMOVAT
    62479: 'Equipment',  # BEVERAGE DISPENSER, CLEAR 5 GAL w/INFUSE
    62475: 'Equipment',  # BEVERAGE DISPENSER, CLEAR-IVORY 5 GAL
    62636: 'Equipment',  # CHAFER, FULLSIZE, ROLLTOP, STAINLESS 8QT
    62633: 'Equipment',  # CHAFER, FULLSIZE, STAINLESS (GOLD TRIM)
    62634: 'Equipment',  # CHAFER, FULLSIZE, STAINLESS STEEL
    62637: 'Equipment',  # CHAFER, HALFSIZE, STAINLESS STEEL
    62654: 'Equipment',  # FOUNTAIN, 3 GAL EMPRESS (6 AMP)
    62651: 'Equipment',  # FOUNTAIN, 3 GAL PRINCESS (6AMP)
    62653: 'Equipment',  # FOUNTAIN, 4 1/2 GAL EMPRESS (6 AMP)
    62652: 'Equipment'   # FOUNTAIN, 7 GAL PRINCESS (6 AMP)
}

def categorize_item(rental_class_id):
    return CATEGORY_MAP.get(int(rental_class_id or 0), 'Other')

def subcategorize_item(category, rental_class_id):
    rid = int(rental_class_id or 0)
    if category in ['Tent Tops', 'Tables and Chairs', 'Round Linen', 'Rectangle Linen', 'Concession']:
        return SUBCATEGORY_MAP.get(rid, 'Unspecified Subcategory')
    return 'Unspecified Subcategory'

@tab2_bp.route("/")
def show_tab2():
    print("Loading /tab2/ endpoint")
    with DatabaseConnection() as conn:
        items = conn.execute("SELECT * FROM id_item_master").fetchall()
        contracts = conn.execute("SELECT DISTINCT last_contract_num, client_name, MAX(date_last_scanned) as scan_date FROM id_item_master WHERE last_contract_num IS NOT NULL GROUP BY last_contract_num").fetchall()
    items = [dict(row) for row in items]
    contract_map = {c["last_contract_num"]: {"client_name": c["client_name"], "scan_date": c["scan_date"]} for c in contracts}

    filter_common_name = request.args.get("common_name", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in (item.get("common_name") or "").lower()]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if filter_tag_id in (item.get("tag_id") or "").lower()]
    if filter_bin_location:
        filtered_items = [item for item in filtered_items if filter_bin_location in (item.get("bin_location") or "").lower()]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if filter_last_contract in (item.get("last_contract_num") or "").lower()]
    if filter_status:
        filtered_items = [item for item in filtered_items if filter_status in (item.get("status") or "").lower()]

    category_map = defaultdict(list)
    for item in filtered_items:
        cat = categorize_item(item.get("rental_class_num"))
        category_map[cat].append(item)

    parent_data = []
    sub_map = {}
    for category, item_list in category_map.items():
        available = sum(1 for item in item_list if item["status"] == "Ready to Rent")
        on_rent = sum(1 for item in item_list if item["status"] in ["On Rent", "Delivered"])
        service = len(item_list) - available - on_rent
        client_name = contract_map.get(item_list[0]["last_contract_num"], {}).get("client_name", "N/A") if item_list and item_list[0]["last_contract_num"] else "N/A"
        scan_date = contract_map.get(item_list[0]["last_contract_num"], {}).get("scan_date", "N/A") if item_list and item_list[0]["last_contract_num"] else "N/A"

        temp_sub_map = defaultdict(list)
        for itm in item_list:
            subcat = subcategorize_item(category, itm.get("rental_class_num"))
            temp_sub_map[subcat].append(itm)

        sub_map[category] = {
            "subcategories": {subcat: {"total": len(items)} for subcat, items in temp_sub_map.items()}
        }

        parent_data.append({
            "category": category,
            "total": len(item_list),
            "available": available,
            "on_rent": on_rent,
            "service": service,
            "client_name": client_name,
            "scan_date": scan_date
        })

    parent_data.sort(key=lambda x: x["category"])
    expand_category = request.args.get('expand', None)

    return render_template(
        "tab2.html",
        parent_data=parent_data,
        sub_map=sub_map,
        expand_category=expand_category,
        filter_common_name=filter_common_name,
        filter_tag_id=filter_tag_id,
        filter_bin_location=filter_bin_location,
        filter_last_contract=filter_last_contract,
        filter_status=filter_status
    )

@tab2_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    print("Hit /tab2/subcat_data endpoint")
    category = request.args.get('category')
    subcat = request.args.get('subcat')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master").fetchall()
    items = [dict(row) for row in rows]

    filter_common_name = request.args.get("common_name", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in (item.get("common_name") or "").lower()]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if filter_tag_id in (item.get("tag_id") or "").lower()]
    if filter_bin_location:
        filtered_items = [item for item in filtered_items if filter_bin_location in (item.get("bin_location") or "").lower()]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if filter_last_contract in (item.get("last_contract_num") or "").lower()]
    if filter_status:
        filtered_items = [item for item in filtered_items if filter_status in (item.get("status") or "").lower()]

    category_items = [item for item in filtered_items if categorize_item(item.get("rental_class_num")) == category]
    subcat_items = [item for item in category_items if subcategorize_item(category, item.get("rental_class_num")) == subcat]

    total_items = len(subcat_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = subcat_items[start:end]

    print(f"AJAX: Category: {category}, Subcategory: {subcat}, Total Items: {total_items}, Page: {page}")

    return jsonify({
        "items": [{
            "tag_id": item["tag_id"],
            "common_name": item["common_name"],
            "status": item["status"],
            "bin_location": item.get("bin_location", "N/A"),
            "quality": item.get("quality", "N/A"),
            "last_contract_num": item.get("last_contract_num", "N/A"),
            "date_last_scanned": item.get("date_last_scanned", "N/A"),
            "last_scanned_by": item.get("last_scanned_by", "N/A"),
            "notes": item.get("notes", "N/A")
        } for item in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })