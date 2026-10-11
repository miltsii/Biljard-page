# Biljardiharjoitukset

Biljardiharjoitukset on web-sovellus, johon käyttäjät voivat lisätä biljardiharjoituksia ja kirjata niille tuloksia. Harjoitus voi olla esimerkiksi "10 potin sarja", ja kuvauksessa kerrotaan, miten harjoitus tehdään ja miten pisteet lasketaan. Toiset käyttäjät voivat tehdä harjoituksen ja kirjata oman tuloksensa.

Sovellus on Helsingin yliopiston Tietokannat ja web-ohjelmointi -kurssin harjoitustyö. Se on tehty Pythonilla ja Flaskilla, ja tiedot tallennetaan SQLite-tietokantaan.

## Sovelluksen toiminnot

- Käyttäjä voi luoda tunnuksen ja kirjautua sisään ja ulos.
- Käyttäjä voi lisätä, muokata ja poistaa omia harjoituksiaan.
- Harjoitukselle valitaan yksi tai useampi luokka, esimerkiksi Pillipallot tai Vallipallot. Luokat ovat tietokannassa.
- Käyttäjä voi kirjata minkä tahansa harjoituksen tuloksen (pisteet 0–10 ja halutessaan muistiinpano). Oman tuloksen voi muokata ja poistaa. Harjoituksen sivulla näkyvät tulokset ja niiden keskiarvo.
- Etusivulla näkyvät kaikki harjoitukset, ja ne voi rajata luokan mukaan.
- Harjoituksia voi hakea hakusanalla otsikosta ja kuvauksesta.
- Käyttäjäsivulla näkyvät käyttäjän harjoitukset sekä harjoitusten ja tulosten määrä ja tulosten keskiarvo.
- Harjoitukset, hakutulokset ja tulokset näytetään sivuissa (10 kerrallaan).

## Sovelluksen käynnistäminen

Tarvitset Pythonin (versio 3.10 tai uudempi).

Hae koodi ja siirry kansioon:

git clone https://github.com/miltsii/Biljard-page.git
cd Biljard-page

Luo virtuaaliympäristö ja asenna Flask.

Linux ja macOS:

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Windows (PowerShell):

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

Luo tietokanta. Komento käyttää tiedostoa `schema.sql`. Windowsissa kirjoita `python` komennon `python3` tilalle.


python3 init_db.py


Käynnistä sovellus:


flask run

Sovellus toimii osoitteessa http://127.0.0.1:5000.

## Sovelluksen testaaminen

1. Luo tunnus sivulla "Rekisteröidy" ja kirjaudu sisään.
2. Valitse "Uusi harjoitus", kirjoita otsikko ja kuvaus ja valitse vähintään yksi luokka.
3. Avaa harjoitus ja kirjaa tulos.
4. Kokeile hakua yläpalkista ja luokkien mukaista rajausta etusivulta.
5. Avaa oma käyttäjäsivusi napsauttamalla käyttäjänimeä yläpalkissa.
6. Luo toinen tunnus ja kirjaa tulos ensimmäisen käyttäjän harjoitukseen. Toisen käyttäjän ei pitäisi pystyä muokkaamaan tai poistamaan ensimmäisen käyttäjän harjoitusta. Osoite `/drill/1/edit` näyttää virheen 403.
7. Kokeile virheellisiä syötteitä, esimerkiksi tyhjää otsikkoa, pisteitä 11 tai liian lyhyttä salasanaa. Lomake näyttää virheilmoituksen.

## Tiedostot

- `app.py`: sivujen reitit, syötteiden tarkistus ja oikeuksien tarkistus
- `db.py`: yleiset tietokantafunktiot
- `users.py`: käyttäjien SQL-kyselyt
- `drills.py`: harjoitusten ja luokkien SQL-kyselyt
- `attempts.py`: tulosten SQL-kyselyt
- `config.py`: asetukset
- `schema.sql`: tietokannan taulut ja luokat
- `init_db.py`: luo tietokannan
- `seed.py`: luo testidataa
- `templates/`: sivupohjat
- `static/style.css`: tyylit

## Tietoturva

- Salasanat tallennetaan hajautettuina.
- Jokaisessa lomakkeessa on CSRF-token, joka tarkistetaan lomaketta käsiteltäessä.
- SQL-kyselyissä käytetään parametreja.
- Sivupohjat escapettaavat käyttäjän kirjoittaman tekstin, joten HTML-koodi ei toimi sivulla.
- Harjoituksen tai tuloksen voi muokata ja poistaa vain sen lisännyt käyttäjä. Muille palvelin näyttää virheen 403. Uuden tiedon lisääminen vaatii kirjautumisen.
- Palvelin tarkistaa syötteet ennen tallennusta: tunnuksen ja salasanan pituuden, otsikon, kuvauksen ja muistiinpanon pituuden, pisteet, valitut luokat, hakusanan pituuden ja sivunumeron.

## Suuri tietomäärä

Tiedosto `seed.py` lisää tietokantaan 1 000 käyttäjää, 100 000 harjoitusta ja miljoona tulosta. Testikäyttäjien tunnukset ovat `user1`, `user2` jne. ja salasana on `testitesti`.

python3 init_db.py
python3 seed.py

Sivut hakevat tiedot sivu kerrallaan (`LIMIT` ja `OFFSET`), joten kaikkia rivejä ei haeta kerralla. Viiteavainsarakkeille on tehty indeksit (esimerkiksi `attempts.drill_id`).

Mittasin sivujen latausajat omalla koneella tällä tietomäärällä. Taulukossa on kahden viimeisen mittauskierroksen pienin ja suurin aika.

| Sivu | Aika |

| Etusivu | 11–12 ms |
| Etusivu, sivu 5000 | 33–37 ms |
| Luokan rajaus, sivu 100 | 84–86 ms |
| Haku | 111–158 ms |
| Harjoituksen sivu | 6–11 ms |
| Käyttäjäsivu | 16–20 ms |

Haku on taulukon hitain, koska se käy läpi koko `drills`-taulun (`LIKE '%...%'`).

## Pylint

Pylint-raportti on tiedostossa [pylint-report.md](pylint-report.md).