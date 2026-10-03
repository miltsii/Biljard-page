# Biljard-page

Keskustelufoorumi biljardin pelaajille. Käyttäjät voivat kirjoittaa viestejä, valita niille aihealueita ja kommentoida toistensa viestejä.

Sovellus on Helsingin yliopiston Tietokannat ja web-ohjelmointi -kurssin harjoitustyö. Se on tehty Pythonilla ja Flaskilla, ja tiedot tallennetaan SQLite-tietokantaan.

## Sovelluksen toiminnot

- Käyttäjä voi luoda tunnuksen ja kirjautua sisään ja ulos.
- Käyttäjä voi lisätä, muokata ja poistaa omia viestejään.
- Viestille valitaan yksi tai useampi aihealue. Aihealueet ovat tietokannassa (Pool, Snooker, Carom, Equipment, Tournaments, General).
- Käyttäjä voi kommentoida muiden viestejä sekä muokata ja poistaa omia kommenttejaan.
- Etusivulla näkyvät kaikki viestit, ja ne voi rajata aihealueen mukaan.
- Viestejä voi hakea hakusanalla.
- Käyttäjäsivulla näkyy käyttäjän viestit sekä viestien ja kommenttien määrä.
- Viestit, hakutulokset ja kommentit on sivutettu.

## Sovelluksen käynnistäminen

Sovellus tarvitsee Pythonin (versio 3.10 tai uudempi).

Hae koodi ja siirry kansioon:

git clone https://github.com/miltsii/Biljard-page.git
cd Biljard-page


Luo virtuaaliympäristö ja asenna Flask:

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


Windowsissa virtuaaliympäristö luodaan ja otetaan käyttöön näin:

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt


Luo tietokanta:


python3 init_db.py


(Windowsissa `python init_db.py`.)

Käynnistä sovellus:

flask run


Sovellus toimii osoitteessa http://127.0.0.1:5000.

## Sovelluksen testaaminen

1. Luo tunnus sivulla "Rekisteröidy" ja kirjaudu sisään.
2. Lisää uusi viesti ja valitse sille aihealueita.
3. Avaa viesti ja kirjoita kommentti.
4. Kokeile hakua ja etusivun aihealuesuodatusta.
5. Avaa oma käyttäjäsivusi napsauttamalla käyttäjänimeä yläpalkissa.
6. Luo toinen tunnus ja tarkista, ettei se pysty muokkaamaan tai poistamaan ensimmäisen käyttäjän viestejä tai kommentteja. Jos kirjoitat osoitteeksi esimerkiksi `/post/1/edit`, sivu antaa virheen 403.
7. Kokeile myös virheellisiä syötteitä, kuten tyhjää otsikkoa tai liian lyhyttä salasanaa. Lomake näyttää virheilmoituksen ja säilyttää kirjoitetun tekstin.

## Tietoturva

- Salasanat tallennetaan hajautettuina (`generate_password_hash`).
- Lomakkeissa on CSRF-token, joka tarkistetaan jokaisessa POST-pyynnössä.
- SQL-komennoissa käytetään parametreja.
- Sivut tehdään `render_template`-funktiolla, joten HTML-koodi ei pääse suoritettavaksi sivulle.
- Käyttäjä voi muokata ja poistaa vain omia viestejään ja kommenttejaan. Muuten palvelin palauttaa virheen 403.
- Palvelin tarkistaa kaikki syötteet ennen tallennusta, esimerkiksi pituudet ja aihealueiden olemassaolon.

## Suuri tietomäärä

Sovellusta testattiin suurella tietomäärällä tiedostolla `seed.py`. Se lisää tietokantaan 1 000 käyttäjää, 100 000 viestiä ja miljoona kommenttia:

```
python3 init_db.py
python3 seed.py
```

Testikäyttäjien tunnukset ovat `user1`, `user2` jne. ja salasana `testitesti`.

Viestit ja kommentit haetaan sivu kerrallaan (`LIMIT` ja `OFFSET`), joten kaikkia rivejä ei haeta kerralla. Tietokantaan on lisätty indeksit viiteavainsarakkeille (esimerkiksi `comments.post_id`).

Tulokset suurella tietomäärällä:

- etusivu ja viestin sivu latautuvat noin 1–20 millisekunnissa
- haku kestää noin 35 ms, koska `LIKE '%...%'` käy läpi koko `posts`-taulun
- ensimmäinen pyyntö heti tietokannan luonnin jälkeen on hitaampi

## Muuta

- Asetukset (salainen avain, tietokannan nimi, sivun koko) ovat tiedostossa `config.py`. Siinä oleva salainen avain on vain kehityskäyttöön.
- Pylint-raportti on tiedostossa `pylint-report.md`.