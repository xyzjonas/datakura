# 2026-03-12 MEETING NOTES

## Nejasnosti

✅ (NIC NEFILTROVAT)
✅ aktivni sklad (lokace) - vazano na session, nutno vzdy zvolit - samotny filtr zatim
✅ filtrovat pouze skladove polozky?
✅ filtrovat produkty?
✅ filtrovat objednavky? Pri zadavani objednavky zobrazovat skladove zasoby pouze vybrane lokace?
✅ prumerna cena - prepocet na dotaz? Co je tim mysleno? = prepocet **PRODEJNICH** cen

## POZNAMKY

### Produkt

✅ - duplikovat produkt
✅ - minule objednavky (table/search) v karte produktu

### Sklad

- vlastni inventura ?
- dostupne oddelit ?

### Objednavka

- typ baleni - volitelne
- kod zakaznika = je potreba mit expedicni stitek
- obchodaci muzou hybat cenou +- % (e.g. 5%)

---

### Objednavka IN

- pridat novy typ baleni v kroku evidence
✅ - kontrola konzistence mnozstvi polozek (i ceny), objednavame zcestne malo? nebo moc? vykricnik!
✅ - moznost editovat celkovou cenu polozky (celkovy! - ne cena za kus) - kus je computed
✅- dobropis vs. doposlani
✅ - nejdriv: odstranit vsechny polozky do nove prijemky (vazba -> primary) a naskladni co jde
✅ - doposlani - bude doreseno v nove sekundarni prijemce
✅ - dobropis - bude (muze byt) doreseno v nove sekundarni prijemce
✅ - potvrzuju pred prijmem fyzickym - v kancelari potvrdim objednavku (na zaklade prijate faktury) a vytvorim prijemku (virtualni) "ceka na dodani"
✅ faktury jako pdf prikladat k objednavce - neni potreba mit v db

### Sklad

✅- moznost vyhodit polozky do nove prijemky a tam si rozhodnu jestli dobropis nebo jestli to prislo (viz vyse)
✅- primarni + n sekundarnich - 1:n vazba (viz vyse)

- evidovat sarzi nehlede na typ baleni/kus

### Produkty

- zakaz evidence/rozpadnuti pro urcite skupiny (i produkt)
- zakaz rozbalovni baleni pro urcite produkty (zakaz kusoveho prodeje)
- soubory (dokumenty) vazat na produkt (certifikace) + poznamka (cislo sarze atp.)

### Cenik

- globalni minimalni cena polozka plosna pro kusovy prodej a v objednavce se prepise a zasviti. Moznost vyclenit urcite zakazniky (VIP) - v karte zakaznika
  ✅ - cena pro zakaznika na urcity produkt/sortiment - maximalni prio
  ✅- cena globalni sleva - skupiny A, B, C - prio podle vyse
- i z pohledu produktu, moznost zakazat slevove skupiny pro urcity produkt
- prumerna cena - prepocet na dotaz. Na klik prepocitat cenove hladiny (neni potreba? computed?)

### Objednavka

✅ - volnych / skladem + na ceste (objednano) - proklik od tama (z badge) + seznam (modal) objednavek

- navazat soubory (vice)
✅- prijata objednavka - castecne vydat a vytvorit novou objednavku (vydejku) na zbytek
✅- faktura MUSI byt v db jako table
✅- faktura navazana na VICE objednavek (souhrnna faktura)
✅- faktury (vazby) vytvaret manualne z jedne nebo vice objednavek
