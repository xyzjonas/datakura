## Prijem

[ ] chyba v souctu hmotnosti - prijemka
[ ] prijmova faktura - schovat generovani pdf - jen odkaz na stazeni nahraneho pdf
[ ] Pole nesmí být číslo větší než 9999 -> 999999
[ ] kontrola konzistence mnozstvi polozek, objednavame zcestne malo? nebo moc? vykricnik! - aritmeticky za poslednich 10
[ ] presun naskladneni nesledovano nezmizi z "polozky k naskladneni"
[ ] presun nesledovaneho produktu podel kodu stock product karty - nenajde (hleda podle product code a ne barcode) - ale jen ve webovem rozhrani


## Tisk
[ ] prijem na stitek: evidencni barkod interni, cislo dodavatele, cislo prijmova objednavka
[ ] vydej na stitek: nazev produktu, pocet v zakladni jednotce (ks), Externí číslo, barkod hlavni produktu ZAKAZNIKA (nastavatitelne v karte produktu)

## Vydej - objednavka
[ ] vizualni indikace ze ten radek (produkt) vyzaduje jejich barkod
[ ] Externí číslo => "cislo objednavky zakaznika"
[x] textove pole pro KAZDOU polozku - jen do objednavky (ne do skladu) - hlavne do pdf
[x] duplikovat objednavku


## Rozbalovani


## Banka
[ ] napojit oberbank, fio - API (korunovy i eurovy)
[ ] moznost vice bank (fio)


## Vyroba
[x] novy modul
[x] technicky objednavka ale musi jit uplne bokem
[x] tyc 1m -> objednavka na vyrobu (rez) vydej ze skladu do vyroby
[x] MUSI ZUSTAT SKLADOVA HODNOTA!!! vydej a zpoetny prijem musi byt celkem 0 rozdil.
[x] cilova karta muze obsahovat jine polozky a musi zapocit do ceny
[x] zachovat vazbu na vstupni produkt (dame to auditu)
[ ] muze byt i externi, rozdil v prijmova cena navysena o sluzbu - vydana cena.
[ ] moznost nahrat fakturu
[x] vydejky/prijemky maji svoji ciselnou rada



DONE
## Ciselne rady

XX-26XXXXX (konfigurovatelne)

- vyjedky: V
- prijemky: P
- kalkulace: N (prejmenovat kalkulace -> nabidka) -> nova polozka v menu (nabidky)
- OP : (prijata)
- OV : (vydana)
- PV : pozadavek vyroby
- ZV : vyroba vydejka
- ZP : vyroba prijemka
- FV : faktura vydana
- FP : faktura prijata