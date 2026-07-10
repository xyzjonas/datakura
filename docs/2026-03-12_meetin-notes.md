# 2026-03-12 MEETING NOTES

## Nejasnosti

[x] (NIC NEFILTROVAT)
[x] aktivni sklad (lokace) - vazano na session, nutno vzdy zvolit - samotny filtr zatim
[x] filtrovat pouze skladove polozky?
[x] filtrovat produkty?
[x] filtrovat objednavky? Pri zadavani objednavky zobrazovat skladove zasoby pouze vybrane lokace?
[x] prumerna cena - prepocet na dotaz? Co je tim mysleno? = prepocet **PRODEJNICH** cen

## POZNAMKY

### Produkt

[x] duplikovat produkt
[x] minule objednavky (table/search) v karte produktu

### Objednavka

[x] typ baleni - volitelne
[ ] kod zakaznika = je potreba mit expedicni stitek
[ ] obchodaci muzou hybat cenou +- % (e.g. 5%)

---

### Objednavka IN

[x] pridat novy typ baleni v kroku evidence
[x] kontrola konzistence mnozstvi polozek (i ceny), objednavame zcestne malo? nebo moc? vykricnik!
[x] moznost editovat celkovou cenu polozky (celkovy! - ne cena za kus) - kus je computed
[x] dobropis vs. doposlani
[x] nejdriv: odstranit vsechny polozky do nove prijemky (vazba -> primary) a naskladni co jde
[x] doposlani - bude doreseno v nove sekundarni prijemce
[x] dobropis - bude (muze byt) doreseno v nove sekundarni prijemce
[x] potvrzuju pred prijmem fyzickym - v kancelari potvrdim objednavku (na zaklade prijate faktury) a vytvorim prijemku (virtualni) "ceka na dodani"
[x] faktury jako pdf prikladat k objednavce - neni potreba mit v db

### Sklad

[x] moznost vyhodit polozky do nove prijemky a tam si rozhodnu jestli dobropis nebo jestli to prislo (viz vyse)
[x] primarni + n sekundarnich - 1:n vazba (viz vyse)
[x] evidovat sarzi nehlede na typ baleni/kus

### Produkty

[ ] zakaz evidence/rozpadnuti pro urcite skupiny (i produkt)
[x] zakaz rozbalovni baleni pro urcite produkty (zakaz kusoveho prodeje)
[ ] soubory (dokumenty) vazat na produkt (certifikace) + poznamka (cislo sarze atp.)

### Cenik

[ ] globalni minimalni cena polozka plosna pro kusovy prodej a v objednavce se prepise a zasviti. Moznost vyclenit urcite zakazniky (VIP) - v karte zakaznika
[x] cena pro zakaznika na urcity produkt/sortiment - maximalni prio
[x] cena globalni sleva - skupiny A, B, C - prio podle vyse
[x] i z pohledu produktu, moznost zakazat slevove skupiny pro urcity produkt
[x] prumerna cena - prepocet na dotaz. Na klik prepocitat cenove hladiny - NENI potreba => computed

### Objednavka

[x] volnych / skladem + na ceste (objednano) - proklik od tama (z badge) + seznam (modal) objednavek
[ ] navazat soubory (vice)
[x] prijata objednavka - castecne vydat a vytvorit novou objednavku (vydejku) na zbytek
[x] faktura MUSI byt v db jako table
[x] faktura navazana na VICE objednavek (souhrnna faktura)
[x] faktury (vazby) vytvaret manualne z jedne nebo vice objednavek

# 2026-04-27 MEETING NOTES

[x] editace prijate dokud neni prijemka
[x] nove baleni popis haze chyba
[x] UX mozna - action btns -> FAB

[ ] multiselect na tisk stitku v prijemce

## vydej
[x] vydej partial item quantities (19.6)

[ ] tisk dodaciho listu (vydejka)
[x] seznam vyfiltrovat podle odberatele
[x] zakaznik prefill splatnosti v kalendarnich dnech, zakladni hodnota 10 kalendarnich

# more

[ ] export produktu do tabulky a zpet po editaci (manualni korekce cen)
[x] snapshot skladu (v manualnim intervlu (e.g. 1x za mesic) -> primarne celkova hodnota zbozi)
[ ] vratky (to be discussed)

# 29.4.2026

[x] uprava vydejky -ze smeru objednavky, upravim JENOM objednavku (uberu pocet, zmenim cenu, pridam polozky) - musi se to propsat do vydejky

[x] kalkulace
