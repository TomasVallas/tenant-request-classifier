# Oppimismuistiinpanot: React ja TypeScript

Tähän on koottu projektissa käytetyt React- ja TypeScript-käsitteet. Tavoitteena on, että osaat selittää jokaisen osan työhaastattelussa omin sanoin.

## Käsitelista

### React

- [x] Komponentti
- [x] JSX
- [x] Props
- [x] State
- [x] `useState`
- [x] Tilan nostaminen
- [x] `useEffect`
- [x] `useRef`
- [x] Tapahtumankäsittely ja lomakkeet
- [x] Listojen renderöinti ja `key`
- [x] Ehdollinen renderöinti

### TypeScript

- [x] Tyypit ja tyyppimerkinnät
- [x] `type` ja `interface`
- [x] Union- ja literaalityypit
- [x] `as const`
- [x] Propsien tyypitys
- [x] Geneeriset tyypit, kuten `Promise<T>`
- [x] `unknown` ja tyyppivahti
- [x] Strict mode

### Selain ja API

- [x] `async` ja `await`
- [x] `fetch` ja virheiden käsittely
- [x] `localStorage`
- [x] Ympäristömuuttujat Vitessä (`VITE_*`)

### Testaus

- [x] Vitest
- [x] React Testing Library
- [x] API-kutsun mockaaminen

## React

### Komponentti

**Mitä se on:** Komponentti on funktio, joka palauttaa käyttöliittymän osan. Sovellus rakennetaan pienistä komponenteista, joita voi käyttää ja testata erikseen.

**Missä projektissa:** `ExampleButtons`, `RequestForm`, `ResultCard`, `HistoryList` ja ne kokoava `App`.

**Näin selitän sen haastattelussa:** Jaoin näkymän komponentteihin niin, että jokaisella on yksi selkeä vastuu.

### JSX

**Mitä se on:** JSX on syntaksi, jolla käyttöliittymä kirjoitetaan HTML:ää muistuttavasti JavaScriptin sisään. Aaltosulkeissa `{}` voi käyttää JavaScript-arvoja. HTML:n `class` on JSX:ssä `className`, ja `for` on `htmlFor`.

**Missä projektissa:** Jokaisen komponentin `return`-osa.

**Näin selitän sen haastattelussa:** JSX kuvaa, miltä näkymän pitäisi näyttää nykyisellä datalla, ja React päivittää selaimen sen mukaan.

### Props

**Mitä se on:** Propsit ovat arvoja, jotka vanhempikomponentti antaa lapselle. Ne ovat lapselle vain luettavia. Lapsi voi viestiä vanhemmalle kutsumalla propsina saamaansa funktiota.

**Missä projektissa:** `ResultCard` saa propsit `result`, `isApproved` ja `onApprove`.

**Näin selitän sen haastattelussa:** Data kulkee propseina alaspäin ja tapahtumat funktiokutsuina ylöspäin.

### State

**Mitä se on:** State on komponentin muisti, joka säilyy renderöintien välillä. Kun state muuttuu, React renderöi komponentin uudelleen. Tavallinen muuttuja ei aiheuta uudelleenrenderöintiä eikä säily sen yli.

**Missä projektissa:** `App` pitää tilassa lomakkeen tekstin, tuloksen, historian, latauksen ja virheen.

**Näin selitän sen haastattelussa:** Pidän tilassa vain sen, mitä ei voi laskea muista arvoista.

### `useState`

**Mitä se on:** `useState` on hook, joka luo tilamuuttujan ja sen päivitysfunktion. Päivitys voi saada uuden arvon tai funktion, joka laskee sen edellisestä arvosta. Alkuarvoksi voi antaa funktion, jolloin se ajetaan vain ensimmäisellä renderöinnillä.

**Missä projektissa:** `useState<HistoryItem[]>(loadHistory)` lukee historian vain kerran kohdassa `App.tsx`.

**Näin selitän sen haastattelussa:** Käytän päivitysfunktiota `setHistory((previous) => ...)`, kun uusi arvo riippuu edellisestä.

### Tilan nostaminen

**Mitä se on:** Kun usea komponentti tarvitsee saman tiedon, tila siirretään niiden yhteiseen vanhempaan. Vanhempi antaa arvon ja muutosfunktion lapsille propseina.

**Missä projektissa:** `text` on `App`-komponentissa, koska sekä `ExampleButtons` että `RequestForm` muuttavat sitä.

**Näin selitän sen haastattelussa:** Yhdellä tiedolla on yksi omistaja, joten näkymät eivät voi joutua keskenään ristiriitaan.

### `useEffect`

**Mitä se on:** `useEffect` ajaa koodia renderöinnin jälkeen ja synkronoi Reactin jonkin ulkoisen asian kanssa. Riippuvuuslista kertoo, milloin efekti ajetaan uudelleen. Efekti voi palauttaa siivousfunktion.

**Missä projektissa:** `App` tallentaa historian `localStorage`:en, ja `ResultCard` siirtää fokuksen sekä nollaa kopiointiviestin ajastimella.

**Näin selitän sen haastattelussa:** Käytän efektiä vain Reactin ulkopuolisiin asioihin, kuten selaimen tallennustilaan ja ajastimiin.

### `useRef`

**Mitä se on:** `useRef` säilyttää arvon renderöintien välillä aiheuttamatta uudelleenrenderöintiä. Sitä käytetään usein viittaamaan suoraan DOM-elementtiin.

**Missä projektissa:** `ResultCard` siirtää fokuksen otsikkoon `headingRef`-viittauksella.

**Näin selitän sen haastattelussa:** Fokuksen siirto auttaa näppäimistön ja ruudunlukijan käyttäjiä sekä vierittää puhelimella tuloksen näkyviin.

### Tapahtumankäsittely ja lomakkeet

**Mitä se on:** Reactissa tapahtumiin liitetään funktio esimerkiksi `onClick`- tai `onSubmit`-propilla. Lomakkeen selainoletus estetään kutsulla `event.preventDefault()`. Kun kentän arvo tulee statesta, sitä kutsutaan kontrolloiduksi kentäksi.

**Missä projektissa:** `RequestForm` tarkistaa tekstin ennen kuin kutsuu `onSubmit`-funktiota.

**Näin selitän sen haastattelussa:** Kontrolloitu kenttä pitää Reactin tilan ja näkyvän arvon aina samana.

### Listojen renderöinti ja `key`

**Mitä se on:** Lista renderöidään yleensä `map`-funktiolla. Jokainen rivi tarvitsee vakaan `key`-arvon, jotta React tunnistaa rivit päivitysten välillä. Kun komponentin `key` vaihtuu, React luo sen uudelleen ja sen tila nollautuu.

**Missä projektissa:** `HistoryList` käyttää `item.id`-arvoa. `App` antaa `ResultCard`-komponentille `key`-arvon, jotta uusi tulos nollaa muokatun vastauksen.

**Näin selitän sen haastattelussa:** En käytä taulukon indeksiä avaimena, koska rivien järjestys muuttuu.

### Ehdollinen renderöinti

**Mitä se on:** JSX:ssä näkymä voi riippua arvosta. Yleisimmät tavat ovat `ehto && <Osa />` ja kolmiosainen `ehto ? <A /> : <B />`.

**Missä projektissa:** `App` valitsee lataus-, virhe-, tyhjän tai tulostilan, ja `ResultCard` näyttää ihmistarkistuksen vain tarvittaessa.

**Näin selitän sen haastattelussa:** Käsittelen jokaisen käyttöliittymän tilan erikseen, jotta käyttäjä näkee aina, mitä tapahtuu.

## TypeScript

### Tyypit ja tyyppimerkinnät

**Mitä se on:** TypeScript lisää JavaScriptiin tyypit, jotka tarkistetaan ennen ajoa. Merkintä `text: string` kertoo, että arvon pitää olla merkkijono. Tyypit poistuvat käännöksessä, joten ne eivät tarkista dataa ajon aikana.

**Missä projektissa:** Kaikki `frontend/src`-kansion tiedostot.

**Näin selitän sen haastattelussa:** Tyypit löytävät virheet jo kehityksessä ja toimivat koodin dokumentaationa.

### `type` ja `interface`

**Mitä se on:** Molemmilla nimetään tyyppi. `interface` sopii hyvin olioiden muodon kuvaamiseen, ja `type` sopii myös esimerkiksi union-tyyppeihin.

**Missä projektissa:** `ClassificationResult` on `interface` ja `Category` on `type` tiedostossa `types.ts`.

**Näin selitän sen haastattelussa:** Käytän `interface`-määrittelyä olioille ja `type`-määrittelyä arvojoukoille.

### Union- ja literaalityypit

**Mitä se on:** Literaalityyppi sallii yhden tarkan arvon, kuten `'vika'`. Union yhdistää useita vaihtoehtoja merkillä `|`. Kääntäjä huomaa, jos koodi käyttää arvoa, jota joukossa ei ole.

**Missä projektissa:** `Category` sallii arvot `vika`, `laskutus`, `muutto` ja `muu`.

**Näin selitän sen haastattelussa:** Sama rajaus on sekä backendin Pydantic-mallissa että frontendin tyypeissä.

### `as const`

**Mitä se on:** `as const` kertoo TypeScriptille, että taulukon arvot ovat tarkkoja ja muuttumattomia. Niistä voidaan johtaa union-tyyppi, jolloin sama lista toimii sekä ajonaikaisena arvona että tyyppinä.

**Missä projektissa:** `CATEGORIES` ja `Category` tiedostossa `types.ts`.

**Näin selitän sen haastattelussa:** Sallitut arvot on määritelty yhdessä paikassa, joten tyyppi ja tarkistus eivät voi erota toisistaan.

### Propsien tyypitys

**Mitä se on:** Komponentin propseille määritellään oma tyyppi. Kääntäjä varoittaa, jos prop puuttuu tai sen tyyppi on väärä.

**Missä projektissa:** Esimerkiksi `RequestFormProps` tiedostossa `RequestForm.tsx`.

**Näin selitän sen haastattelussa:** Props-tyyppi on komponentin julkinen rajapinta.

### Geneeriset tyypit, kuten `Promise<T>`

**Mitä se on:** Geneerinen tyyppi saa toisen tyypin parametrina. `Promise<ClassificationResult>` tarkoittaa lupausta, joka valmistuttuaan antaa luokittelutuloksen. Samalla idealla `useState<string | null>` kertoo tilan tyypin.

**Missä projektissa:** `classify`-funktio tiedostossa `api.ts`.

**Näin selitän sen haastattelussa:** Geneeriset tyypit säilyttävät tarkan tyypin myös uudelleenkäytettävässä koodissa.

### `unknown` ja tyyppivahti

**Mitä se on:** `unknown` tarkoittaa arvoa, jota ei saa käyttää ennen sen tarkistamista. Tyyppivahti on funktio, jonka paluutyyppi on muotoa `value is Tyyppi`. Kun tarkistus onnistuu, TypeScript tietää arvon tyypin.

**Missä projektissa:** `isClassificationResult` tiedostossa `api.ts` ja `isHistoryItem` tiedostossa `history.ts`.

**Näin selitän sen haastattelussa:** Verkosta tai selaimen tallennustilasta tuleva data tarkistetaan ajon aikana, koska TypeScript ei voi taata sitä.

### Strict mode

**Mitä se on:** `strict: true` ottaa käyttöön TypeScriptin tiukat tarkistukset. Silloin esimerkiksi mahdollisesti puuttuva arvo pitää käsitellä, eikä tyyppi saa jäädä huomaamatta `any`-tyypiksi.

**Missä projektissa:** `tsconfig.app.json` ja `tsconfig.node.json`.

**Näin selitän sen haastattelussa:** Strict mode siirtää monet ajonaikaiset virheet käännösvaiheeseen.

## Selain ja API

### `async` ja `await`

**Mitä se on:** `async`-funktio palauttaa aina Promisen. `await` odottaa Promisen valmistumista estämättä käyttöliittymää. Virheet käsitellään tavallisella `try`/`catch`-rakenteella.

**Missä projektissa:** `handleSubmit` tiedostossa `App.tsx` ja `classify` tiedostossa `api.ts`.

**Näin selitän sen haastattelussa:** Lataustila nollataan `finally`-lohkossa, joten painike palautuu myös virheen jälkeen.

### `fetch` ja virheiden käsittely

**Mitä se on:** `fetch` tekee HTTP-pyynnön. Se heittää virheen vain verkko-ongelmissa, joten vastaukset kuten 422 tai 503 pitää tarkistaa kentästä `response.ok`.

**Missä projektissa:** `classify` käsittelee verkkovirheen, aikakatkaisun, palvelimen virheen ja väärän vastausmuodon.

**Näin selitän sen haastattelussa:** Muutan tekniset virheet käyttäjälle selkeiksi suomenkielisiksi viesteiksi yhdessä paikassa.

### `localStorage`

**Mitä se on:** `localStorage` tallentaa merkkijonoja selaimeen myös sivun latausten yli. Se voi olla estetty tai täynnä, ja tallennettu data voi olla rikki.

**Missä projektissa:** `history.ts` käärii luvun ja kirjoituksen `try`/`catch`-rakenteeseen.

**Näin selitän sen haastattelussa:** Tallennan vain luokan, kiireellisyyden, ajan ja tilan, en pyynnön tekstiä, jotta selaimeen ei jää vuokralaisen tietoja.

### Ympäristömuuttujat Vitessä (`VITE_*`)

**Mitä se on:** Vite tuo `VITE_`-alkuiset muuttujat koodiin kohdassa `import.meta.env`. Ne päätyvät selaimelle lähetettävään koodiin, joten niihin ei saa laittaa salaisuuksia.

**Missä projektissa:** `VITE_API_URL` tiedostossa `api.ts`.

**Näin selitän sen haastattelussa:** API-avain on vain backendissä, ja frontend tietää ainoastaan backendin osoitteen.

## Testaus

### Vitest

**Mitä se on:** Vitest on Viten kanssa toimiva testikehys. `describe` ryhmittelee testit, `it` määrittää yhden testin ja `expect` tarkistaa tuloksen. jsdom tarjoaa testeille selaimen kaltaisen ympäristön.

**Missä projektissa:** `frontend/src`-kansion `*.test.ts`- ja `*.test.tsx`-tiedostot.

**Näin selitän sen haastattelussa:** Testit ajetaan ilman oikeaa selainta tai verkkoa, joten ne ovat nopeita ja toistettavia.

### React Testing Library

**Mitä se on:** React Testing Library testaa komponentteja käyttäjän näkökulmasta. Elementit haetaan roolin, nimen tai labelin perusteella, ja `user-event` simuloi klikkauksia ja kirjoittamista.

**Missä projektissa:** Esimerkiksi `RequestForm.test.tsx` varmistaa, että tyhjää pyyntöä ei lähetetä.

**Näin selitän sen haastattelussa:** Testaan käyttäytymistä enkä toteutusta, joten testit auttavat myös saavutettavuudessa.

### API-kutsun mockaaminen

**Mitä se on:** Mockaus korvaa oikean riippuvuuden testissä hallitulla versiolla. Näin voidaan kokeilla onnistumista, virhettä ja latausta ilman oikeaa palvelinta.

**Missä projektissa:** `App.test.tsx` mockaa `classify`-funktion, ja `api.test.ts` mockaa `fetch`-funktion.

**Näin selitän sen haastattelussa:** Testit eivät käytä verkkoa, API-avainta tai maksullista kielimallia.
