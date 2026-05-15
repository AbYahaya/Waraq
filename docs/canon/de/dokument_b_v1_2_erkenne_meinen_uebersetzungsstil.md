<!-- Converted from "DOKUMENT B v1.2 - Erkenne meinen Übersetzungsstil.docx" via pandoc 3.9.0.2 on 2026-05-02 -->
<!-- The .docx in this directory remains source-of-truth per docs/canon/README.md authority rule -->
<!-- Conversion is content-faithful (text, tables, identifiers, Swiss German ss, Arabic RTL spans, §-refs); Word-specific visual styling is dropped -->

**WARAQ – DOKUMENT B v1.2 Strukturierte Feature-Spezifikation: „Erkenne meinen Übersetzungsstil" Grundlage: Dokument A (Kanonischer Nutzerstil-Korpus v1.0)**

**Kein Code. Keine Coding-Freigabe. Kein stilles Re-Baselining. Keine neue Feature-Ausweitung. Dieses Dokument ersetzt keine bestehende Baseline, keine Übergabemappe und keine allgemeine Systemregel.**

**VORRANGLOGIK (ZENTRAL – UNVERÄNDERLICH)**

**Bei jedem Konflikt gilt diese Reihenfolge. Sie wird in diesem Dokument an keiner Stelle verändert:**

1.  **Bereits freigegebene allgemeine Systemregeln (Dokument 1 und Baselines v1.0)\**

    - **Transliteration (EI2 mit Q/J-Anpassung)**

    - **Glossar (Vorrang vor allem, nie automatisch überschreibbar)**

    - **Terminologie-Verzeichnis**

    - **Religiöse Formeln-Verzeichnis**

    - **Qurʾān-Stellenbehandlung gemäss §4.15 (arabischer Qurʾān-Referenzbestand für arabischen Referenztext und Vokalisierung; quranenc.com bzw. lokale Fallback-Kopie für Zielsprachen-Übersetzungen)**

    - **Hadith-Behandlung (Verifikationsquellen-Hierarchie)**

    - **Fachbegriff-Behandlung (erstes Auftreten / Folgeauftreten)**

    - **Alle sonstigen kanonischen Standards aus Dokument 1 und Baselines v1.0**

2.  **Kanonischer Nutzerstil (Dokument A / dieses Feature)\**

    - **Harte Stil-Invarianten (Abschnitt 4 in Dokument A)**

    - **Starke Präferenzen (Abschnitt 5)**

    - **Strukturierte Stilmerkmale (Abschnitt 6)**

3.  **Einzelne Referenzsätze (Referenzkorpus aus Dokument A)\**

    - **Als strukturierte zweisprachige Stilbelege**

    - **Nicht als stiller Ersatz für Systemregeln**

**Wenn ein Referenzsatz eine Schreibweise enthält, die einer Systemregel widerspricht:**

- **Die Systemregel hat Vorrang**

- **Der Referenzsatz bleibt stilistisch massgeblich**

- **Die konkrete Schreibweise wird an die kanonische Systemregel angepasst**

**LESEHILFE: MARKIERUNGEN IN DIESEM DOKUMENT**

**Jede Regel in diesem Dokument ist mit einer der folgenden Markierungen versehen:**

| **Markierung** | **Bedeutung** |
|----|----|
| **\[KANON\]** | **Harte kanonische Regel – unveränderlich, kein Ermessen** |
| **\[KONFIG\]** | **Produktkonfigurierbar – Produktentscheidung, aber nicht durch Lernlogik veränderbar** |
| **\[KALIB\]** | **Kalibrierbar – Schwellenwert noch nicht festgelegt, nach Gold-Corpus-Tests zu bestimmen** |

1.  **ZWECK DES FEATURES**

**1.1 Kernzweck \[KANON\] Das Feature ermöglicht es dem System, den individuellen Übersetzungsstil eines bestimmten Nutzers aus bestätigten zweisprachigen Übersetzungspaaren strukturiert zu erlernen und diesen Stil bei künftigen KI-gestützten Übersetzungsvorschlägen zu berücksichtigen.**

**1.2 Abgrenzung zu Option A \[KANON\] Option A (KI-Standard) ist immer die Ausgangslage. Das Stilfeature ist eine zusätzliche Schicht, die den KI-Standard nutzerspezifisch verfeinert. Es ist kein Ersatz für Option A.**

**1.3 Was das Feature nicht leistet → Siehe Abschnitt 13 (Explizite Ausgrenzungen).**

2.  **AKTIVIERUNGSLOGIK UND FREISCHALTBEDINGUNGEN**

**2.1 Accountbindung \[KANON\] Das Stilfeature ist ausschliesslich und absolut accountgebunden:**

- **Nutzerspezifisch – nicht global.**

- **Nicht Standard für neue Accounts – kein Auto-Start.**

- **Nicht auf andere Accounts übertragbar – weder automatisch noch manuell.**

- **Keine Teilen-Funktion für dieses Feature vorgesehen.**

**Eine mögliche spätere Teilen-Funktion für Stilprofile ist kein Bestandteil dieses Features und erfordert einen separaten CR-Durchlauf. Sie darf nicht aus dem allgemeinen Abo-Konfigurationsrahmen auf dieses Feature übertragen werden.**

**2.2 Freischaltbedingungen**

**Harte kanonische Bedingungen – immer gültig, unabhängig von Produktkonfiguration:**

| **Bedingung** | **Typ** | **Wert** |
|----|----|----|
| **Referenzsätze sind bestätigte Endfassungen** | **\[KANON\]** | **Ja – keine Entwürfe, keine Zwischenstände** |
| **Referenzsätze sind zweisprachig (AR + DE)** | **\[KANON\]** | **Ja – beide Sprachen vollständig** |
| **Explizite Aktivierung durch Nutzer** | **\[KANON\]** | **Pflicht – kein Auto-Aktivieren** |
| **Mindestanzahl bestätigter Referenzsatz-Paare** | **\[KALIB\]** | **Noch nicht festgelegt** |

**Produktkonfigurierbare Bedingungen – Produktentscheidung, nicht Kanon:**

| **Bedingung** | **Typ** | **Bemerkung** |
|----|----|----|
| **Abo-Freischaltung des Features** | **\[KONFIG\]** | **Ja/Nein per Abo-Konfiguration** |
| **Zulässige Accountklassen** | **\[KONFIG\]** | **Produktentscheidung – welche Klassen Zugang erhalten (z. B. Stufe 1 / Stufe 2); konkrete Accountklassen wie Gast, Bewerber, Stufe 1, Stufe 2 sind Produktkonfiguration, nicht Kanon** |

**Wichtig: Welche Accountklassen konkret Zugang erhalten, ist produktkonfigurierbar. Kanonisch ist nur, dass das Feature accountgebunden ist und eine explizite Nutzeraktivierung erfordert. Aussagen wie „gilt nicht für Gast-Accounts" sind Produktkonfiguration, keine harte kanonische Regel.**

**2.3 Deaktivierung \[KANON\]**

- **Der Nutzer kann das Stilprofil jederzeit deaktivieren.**

- **Bereits überarbeitete Seiten werden nicht rückgängig gemacht.**

- **Das Stilprofil bleibt gespeichert und kann reaktiviert werden.**

3.  **ZULÄSSIGE DATENQUELLEN UND LERNQUELLEN-ASYMMETRIE**

**3.1 Grundsatz der Lernquellen-Asymmetrie \[KANON\] Nicht alle Quellen dürfen gleichwertig auf das Stilprofil einwirken. Die folgende Asymmetrie ist harter Kanon und darf durch keine Lernlogik aufgehoben werden:**

| **Quelle** | **Darf neue starke Regeln begründen** | **Darf Invarianten setzen** | **Darf Regeln verstärken** | **Darf schwache Kandidaten erzeugen** | **Signal bei Nichtnutzung** |
|----|----|----|----|----|----|
| **Bestätigte Referenzsätze / Endfassungen (zweisprachig)** | **Ja** | **Nein (nur via Nutzerbestätigung)** | **Ja** | **Ja** | **–** |
| **Manuell eingegebene Stilregeln des Nutzers** | **Ja** | **Ja – direkt** | **Ja** | **Ja** | **–** |
| **Akzeptierte KI-Vorschläge** | **Nein** | **Nein** | **Ja (bestehende Regeln)** | **Ja (nur schwach)** | **–** |
| **Korrigierte KI-Vorschläge** | **Nein** | **Nein** | **Nein** | **Nein** | **Gegensignal / Korrektursignal** |
| **Ignorierte KI-Vorschläge** | **Nein** | **Nein** | **Nein** | **Nein** | **Null Signal** |

**Ausdrücklicher Hinweis zu manuellen Stilregeln \[KANON\]: Auch manuell eingegebene Stilregeln des Nutzers unterliegen vollumfänglich der Vorranglogik dieses Dokuments. Sie dürfen niemals Systemregeln überschreiben oder unterlaufen. Wenn eine manuell eingegebene Stilregel mit einer Systemregel (Glossar, Transliteration, Terminologie-Verzeichnis, religiöse Formeln, Koranvers-Behandlung, Hadith-Verifikationslogik) kollidiert, gilt: die Systemregel hat Vorrang, die manuelle Stilregel wechselt in den Status unterdrückt_durch_systemregel, und der Nutzer wird informiert. Eine manuelle Stilregel kann diesen Vorrang nicht aufheben.**

**3.2 Präzisierung: Was akzeptierte KI-Vorschläge dürfen und was nicht \[KANON\]**

**Akzeptierte KI-Vorschläge dürfen:**

- **Den Konfidenzwert eines bereits aus Referenzsätzen abgeleiteten Eintrags erhöhen.**

- **Einen schwachen Kandidaten (Status: in_prüfung) erzeugen, der noch keine Regelwirkung hat.**

**Akzeptierte KI-Vorschläge dürfen nicht:**

- **Allein eine starke Präferenzregel erzeugen.**

- **Allein eine harte Invariante erzeugen.**

- **Eine bestehende Systemregel untergraben.**

- **Eine bestehende harte Invariante abschwächen.**

**3.3 Korrektursignal \[KANON\] Wenn der Nutzer einen KI-Vorschlag korrigiert, ist dies ein Gegensignal:**

- **Der betroffene Stil-Eintrag wird in seiner Konfidenz gesenkt.**

- **Wenn dasselbe Muster wiederholt korrigiert wird: Eintrag in Negativliste (Status: vom_nutzer_gesperrt).**

- **Keine automatische Inversion ohne Nutzerbestätigung.**

**3.4 Nicht zulässige Quellen \[KANON\] Diese Quellen dürfen unter keinen Umständen in das Stilprofil einfliessen:**

- **Unbestätigte Entwürfe oder Zwischenstände.**

- **Fremde Nutzerprofile / andere Accounts.**

- **Ignorierte KI-Vorschläge.**

- **Glossar-Einträge (Systemregel, kein Stilmuster).**

- **Transliterationsregeln (Systemregel).**

- **Religiöse Formeln-Verzeichnis (Systemregel).**

- **Koranvers-Wiedergaben via quranenc.com (externe Quelle).**

- **Hadith-Texte (Verifikationslogik).**

- **Vokalisierungskorrekturen (separat gespeichert, kein Stilmuster).**

4.  **ANALYSE- UND AUSRICHTUNGSEBENE (ZWEISPRACHIG)**

**4.1 Grundsatz \[KANON\] Stilregeln beruhen nicht auf einem losen Satzpaar-Speicher. Sie beruhen auf strukturiert extrahierten zweisprachigen Belegen, die einem definierten Ausrichtungsmodell folgen. Jede Stilregel muss auf mindestens einem solchen strukturierten Beleg beruhen.**

**4.2 Struktur eines zweisprachigen Stilbelegs**

**Jeder Stilbeleg ist ein strukturierter Datensatz mit folgenden Pflichtfeldern:**

| **Feld** | **Typ** | **Inhalt** |
|----|----|----|
| **beleg_uuid** | **UUID** | **Eindeutige ID des Belegs** |
| **account_uuid** | **UUID** | **Besitzender Account (Accountbindung, siehe §2.1)** |
| **arabisches_muster** | **Text** | **Arabisches Ausgangsmuster (Wort / Konstruktion / Partikel / Phrase)** |
| **arabischer_kontext** | **Text** | **Arabischer Satzkontext, in dem das Muster auftritt** |
| **deutsche_wiedergabe** | **Text** | **Tatsächliche deutsche Wiedergabe im bestätigten Referenzsatz** |
| **phänomenfeld** | **Enum** | **Eines der 12 Phänomenfelder (siehe 4.3)** |
| **belegtyp** | **Enum** | **referenzsatz / endfassung / manuelle_regel** |
| **regeltyp** | **Enum** | **invariant / präferenz / tendenz / kandidat** |
| **konfidenz** | **Float 0.0–1.0** | **Aktuelle Konfidenz** |
| **referenz_paar_uuid** | **UUID** | **Verweis auf das bestätigte AR/DE-Paar als Quelle** |
| **nutzer_bestätigt** | **Boolean** | **Wurde dieser Beleg explizit durch den Nutzer bestätigt** |
| **erstellt_at** | **Timestamp** |  |

**Der Stilbeleg verweist über referenz_paar_uuid auf das zweisprachige Referenzpaar als Provenienzquelle. Das Referenzpaar wird als eigenständiges Objekt geführt:**

| **Feld**               | **Typ**       | **Inhalt**                          |
|------------------------|---------------|-------------------------------------|
| **referenz_paar_uuid** | **UUID**      | **Eindeutige ID des Paars**         |
| **account_uuid**       | **UUID**      | **Besitzender Account**             |
| **arabischer_text**    | **Text**      | **Arabisches Original**             |
| **deutscher_text**     | **Text**      | **Deutsche Endfassung (bestätigt)** |
| **bestätigt_at**       | **Timestamp** | **Zeitpunkt der Nutzerbestätigung** |

**4.3 Phänomenfelder \[KANON\]**

**Die Phänomenfelder entsprechen den in Dokument A, Abschnitt 7 definierten Bereichen:**

| **Nr.** | **Phänomenfeld** |
|----|----|
| **PF-01** | **Partikelbehandlung (<span dir="rtl">وَ / فَ / ثُمَّ / بَل / إِنَّ / ل</span>َ etc.)** |
| **PF-02** | **Satzverknüpfung und Wiederholung** |
| **PF-03** | **Idāfa-Behandlung (Genitivkonstruktionen)** |
| **PF-04** | **Masdar-/Verb-Beziehung** |
| **PF-05** | **Fachgleichsetzungen** |
| **PF-06** | **Umgang mit Qurʾān- und Ḥadīṯ-Zitaten** |
| **PF-07** | **Isnād-/ḥadīṯ-kritische Fachsprache** |
| **PF-08** | **Klammergebrauch** |
| **PF-09** | **Religiös-polemische Begriffe** |
| **PF-10** | **Juristisch-vertragliche Metaphorik** |
| **PF-11** | **Registerhöhe** |
| **PF-12** | **Fehler, die nicht wieder passieren dürfen (Negativliste)** |

**4.4 Extraktion von Stilbelegen aus Referenzsatzpaaren**

**Wenn ein neues bestätigtes AR/DE-Referenzpaar aufgenommen wird, läuft folgende Sequenz ab:**

1.  **System analysiert das Paar und schlägt strukturierte Stilbelege vor (pro erkanntem Phänomenfeld einen oder mehrere Einträge).**

2.  **Nutzer prüft die vorgeschlagenen Stilbelege und entscheidet für jeden Beleg einzeln:**

    - **Bestätigen – Beleg wird unverändert übernommen.**

    - **Verwerfen – Beleg wird nicht aufgenommen; kein Eintrag, kein Signal.**

    - **Präzisiert übernehmen – Nutzer ändert oder präzisiert den vorgeschlagenen Beleg (z. B. arabisches Muster, deutsche Wiedergabe oder Phänomenfeld-Zuordnung) und bestätigt dann die präzisierte Fassung; die präzisierte Fassung gilt als Endfassung des Belegs.**

3.  **Nur bestätigte oder präzisiert übernommene Belege werden in die Ausrichtungsebene aufgenommen.**

4.  **Aufgenommene Belege erhöhen die Konfidenz bestehender Einträge oder erzeugen neue Einträge.**

5.  **Eine neue Stilprofil-Version wird angelegt.**

**\[KANON\]: Schritt 2 (Nutzerbestätigung oder -präzisierung) ist nicht übergehbar. Kein Stilbeleg wird ohne explizite Nutzerhandlung aufgenommen. Ein verworfener Beleg erzeugt keinerlei Signal – auch keinen Kandidaten.**

**4.5 Mindestbelegdichte pro Phänomenfeld \[KALIB\] Bevor ein Phänomenfeld-Muster als Präferenzregel eingestuft wird, ist eine Mindestbelegdichte erforderlich. Konkrete Schwellenwerte: noch nicht festgelegt – nach Gold-Corpus-Tests zu kalibrieren.**

**Felder mit ungenügender Belegdichte werden dem Nutzer als „noch nicht ausreichend gelernt" angezeigt.**

5.  **STRUKTUR DES STILPROFILS (STIL-MATRIX)**

**Das Stilprofil ist nicht als Fliesstext gespeichert, sondern als strukturierte Stil-Matrix.**

**5.1 Dimensionen der Stil-Matrix**

**Dimension 1: Lexikalische Ebene**

| **Feld** | **Phänomenfelder** | **Inhalt** |
|----|----|----|
| **Fachterm-Gleichsetzungen** | **PF-05** | **AR-Wort → bevorzugte DE-Wiedergabe** |
| **Synonymvermeidung** | **PF-05** | **Systematisch gemiedene Alternativen** |
| **Klammergebrauch** | **PF-08** | **Welche Klammerpräzisierungen regelbestimmt sind** |
| **Partikelbehandlung** | **PF-01** | **Wiedergabe von <span dir="rtl">وَ / فَ / ثُمَّ / بَل / إِنَّ / ل</span>َ etc.** |

**Dimension 2: Syntaktische Ebene**

| **Feld** | **Phänomenfelder** | **Inhalt** |
|----|----|----|
| **Satzbewegung** | **PF-02** | **Grad der Spiegelung der arabischen Satzbewegung** |
| **Verknüpfungsketten** | **PF-02** | **Bevorzugte Wiedergabe von Verknüpfungen** |
| **Idafa-Behandlung** | **PF-03** | **Bevorzugtes Muster für Genitivkonstruktionen** |
| **Masdar/Verb-Beziehung** | **PF-04** | **Nomen vs. Verb bei Masdar-Konstruktionen** |

**Dimension 3: Rhetorische Ebene**

| **Feld** | **Phänomenfelder** | **Inhalt** |
|----|----|----|
| **Wiederholungsverhalten** | **PF-02** | **Ob Parallelismen sichtbar gehalten werden** |
| **Intensitätserhalt** | **PF-09** | **Wie Emphase und Zuspitzung erhalten bleiben** |
| **Bildsprache** | **PF-10** | **Ob Metaphern wörtlich bleiben oder mit Klammer** |

**Dimension 4: Fachsprachliche Ebene**

| **Feld** | **Phänomenfelder** | **Inhalt** |
|----|----|----|
| **Hadith-kritische Sprache** | **PF-07** | **Bevorzugte Wiedergabe technischer Termini** |
| **Juristisch-vertragliche Sprache** | **PF-10** | **Ton und Metaphorikerhalt** |
| **Polemisch-argumentative Sprache** | **PF-09** | **Grad der Härteerhaltung** |
| **Registerhöhe** | **PF-11** | **Gesamtregister (gehoben / textnah / klassisch)** |

**Dimension 5: Zitationsverhalten**

| **Feld** | **Phänomenfelder** | **Inhalt** |
|----|----|----|
| **Qurʾān-Zitation** | **PF-06** | **Ob Verse ausgeschrieben oder nur referenziert werden** |
| **Ḥadīṯ-Einbettung** | **PF-06** | **Wie Zitate in den Fliesstext integriert werden** |

**Dimension 6: Negativliste**

| **Feld** | **Phänomenfelder** | **Inhalt** |
|----|----|----|
| **Gesperrte Muster** | **PF-12** | **Systematisch abgelehnte Muster aus Korrektursignalen** |

**5.2 Pro Stil-Eintrag gespeicherte Metadaten**

| **Feld** | **Typ** | **Inhalt** |
|----|----|----|
| **stil_regel_uuid** | **UUID** | **Eindeutige ID** |
| **account_uuid** | **UUID** | **Besitzender Account (Accountbindung, siehe §2.1)** |
| **dimension** | **Enum** | **lexikalisch / syntaktisch / rhetorisch / fachsprachlich / zitationsverhalten / negativ** |
| **phänomenfeld** | **Enum** | **PF-01 bis PF-12** |
| **arabisches_muster** | **Text** | **Arabisches Ausgangsmuster** |
| **bevorzugte_wiedergabe** | **Text** | **Bevorzugte deutsche Wiedergabe** |
| **konfidenz** | **Float 0.0–1.0** | **Aktuelle Konfidenz** |
| **belege_uuids\[\]** | **UUID\[\]** | **Verweise auf bestätigte zweisprachige Stilbelege** |
| **status** | **Enum** | **Siehe Abschnitt 8.2** |
| **regeltyp** | **Enum** | **invariant / präferenz / tendenz / kandidat** |
| **invariant_quelle** | **Enum** | **manuell_nutzer / nutzerbestätigung / nicht_invariant** |
| **erstellt_aus** | **Enum** | **referenzsatz / endfassung / manuelle_regel / akzeptanz_ki / korrektur_ki** |
| **erstellt_at** | **Timestamp** |  |
| **zuletzt_aktualisiert_at** | **Timestamp** |  |

**5.3 Accountbindung der Stilprofil-Objekte \[KANON\] Alle Stilprofil-Objekte (Stil-Eintrag, Stilbeleg, Referenzpaar, Stilprofil-Version) sind an account_uuid gebunden. Kein Cross-Account-Zugriff. Keine technische Freigabe an andere Accounts. Die konkrete Durchsetzung erfolgt auf Daten- und Abfrageebene und ist Teil jeder Stilprofil-Operation.**

6.  **HARTE INVARIANTEN, PRÄFERENZREGELN UND STATISTISCHE TENDENZEN**

**6.1 Grundsatz der strikten Trennung \[KANON\] Die drei Regeltypen dürfen niemals unscharf ineinanderlaufen. Das System darf nicht aus blosser Statistik selbständig eine harte Invariante erzeugen. Übergänge zwischen Typen erfordern immer eine explizite Nutzerhandlung.**

**6.2 Harte Invarianten (regeltyp = invariant) \[KANON\]**

**Was sie sind: Regeln, die durch die Lernlogik nie verändert, nie abgesenkt und nie überschrieben werden. Sie können nur durch eine explizite Nutzerhandlung geändert werden.**

**Wie eine Invariante entsteht – ausschliesslich durch:**

- **Explizite manuelle Nutzerfestlegung (manuell eingegebene Stilregel).**

- **Explizite Nutzerbestätigung einer vom System vorgeschlagenen Invariante.**

**Wie eine Invariante nicht entstehen darf:**

- **Nicht durch statistische Häufung von akzeptierten KI-Vorschlägen.**

- **Nicht durch automatische Hochstufung aus Tendenzen oder Präferenzen.**

- **Nicht durch Systemlogik ohne Nutzerhandlung.**

**Vorankerte Invarianten aus Dokument A (gelten ab Aktivierung des Features):**

- **Absolute Worttreue (keine stillen Auslassungen, keine stillen Vereinfachungen).**

- **Strukturelle Nähe zum Arabischen (Satzbewegung, Reihenfolge).**

- **Wiederholungen bleiben sichtbar.**

- **Keine Verflachung religiöser und fachlicher Begriffe.**

- **Keine stillen Erklärungen (nur offene Klammern).**

- **Kein modernes oder lockeres Deutsch (Register: gehoben, textnah, klassisch).**

**Diese Invarianten sind mit invariant_quelle = manuell_nutzer vorbelegt und in der UI gesondert ausgewiesen.**

**6.3 Gelernte Präferenzregeln (regeltyp = präferenz)**

**Was sie sind: Muster mit hoher Konfidenz, die in der Regel angewendet werden, aber durch kontextuelle Signale zurückgestellt werden können.**

**Wie eine Präferenzregel entsteht:**

- **Aus bestätigten Referenzsätzen / Endfassungen (ausreichende Belegdichte vorausgesetzt).**

- **Aus manuell eingegebenen Stilregeln (direkt als Präferenz oder Invariante).**

- **Nicht aus akzeptierten KI-Vorschlägen allein.**

**Konfidenz-Schwelle für automatische Anwendung: \[KALIB\] – noch nicht festgelegt.**

**6.4 Statistische Tendenzen (regeltyp = tendenz)**

**Was sie sind: Muster, die erkannt wurden, aber noch zu wenig belegt sind für eine Präferenzregel. Das System schlägt sie vor, wendet sie aber nicht automatisch an.**

**Wie eine Tendenz entsteht:**

- **Aus wenigen Belegen in Referenzsätzen.**

- **Aus schwachen Kandidaten, die durch akzeptierte KI-Vorschläge verstärkt wurden.**

**Konfidenz-Schwelle: \[KALIB\] – noch nicht festgelegt.**

**6.5 Kandidaten (regeltyp = kandidat)**

**Was sie sind: Schwächste Kategorie. Muster, die einmal beobachtet wurden (z. B. durch einen akzeptierten KI-Vorschlag), aber noch keinen Regelstatus haben. Keine Anwendung. Kein Vorschlag. Nur Beobachtung.**

**Hochstufung: Nur durch Nutzerbestätigung oder durch neue bestätigte Referenzsatzbelege. Nie durch weitere akzeptierte KI-Vorschläge allein.**

**6.6 Hochstufungsregeln (Übergang zwischen Typen)**

| **Von** | **Nach** | **Bedingung** |
|----|----|----|
| **kandidat** | **tendenz** | **Mindestbelegdichte aus Referenzsätzen \[KALIB\] oder Nutzerbestätigung** |
| **tendenz** | **präferenz** | **Höhere Belegdichte \[KALIB\] oder Nutzerbestätigung** |
| **präferenz** | **invariant** | **Nur durch explizite Nutzerhandlung \[KANON\]** |
| **invariant** | **präferenz** | **Nur durch explizite Nutzerhandlung \[KANON\]** |
| **jeder Typ** | **vom_nutzer_gesperrt** | **Explizite Nutzeraktion oder wiederholtes Korrektursignal** |

7.  **REFERENZSATZ-BINDUNG (ZWEISPRACHIG)**

**7.1 Anforderungen an einen gültigen Referenzsatz \[KANON\]**

| **Kriterium** | **Anforderung** |
|----|----|
| **Arabisches Original** | **Vollständig vorhanden** |
| **Deutsche Endfassung** | **Vollständig vorhanden und durch Nutzer als Endfassung bestätigt** |
| **Bestätigung** | **Explizite Nutzerbestätigung – keine automatische Aufnahme** |
| **Format** | **Zweisprachiges Paar (AR + DE) – nicht monolingual** |
| **Status** | **Endfassung – kein Entwurf, kein Zwischenstand** |

**7.2 Stilsignal-Extraktion → Ablauf: siehe Abschnitt 4.4.**

**7.3 Referenzsatz-Versionierung \[KANON\] Wenn eine Endfassung durch den Nutzer revidiert wird:**

- **Die daraus abgeleiteten Stilbelege werden markiert und einer Neuauswertung unterzogen.**

- **Der Nutzer wird informiert und zur Neubestätigung aufgefordert.**

- **Bereits angewendete Stilmuster auf abgeschlossenen Seiten bleiben unveränderlich.**

8.  **KONFLIKTLOGIK MIT SYSTEMREGELN UND ZUSTANDSMODELL**

**8.1 Grundsatz \[KANON\] Systemregeln haben immer Vorrang vor Stilprofil-Regeln. Das Stilprofil darf Systemregeln weder überschreiben noch untergraben. Keine stillen Entscheidungen bei Konflikten.**

**8.2 Zustandsmodell für Stil-Einträge**

**Jeder Stil-Eintrag befindet sich in genau einem der folgenden Zustände:**

| **Status** | **Bedeutung** |
|----|----|
| **aktiv** | **Regel ist aktiv und wird angewendet** |
| **in_prüfung** | **Kandidat – beobachtet, aber noch kein Regelstatus; keine Anwendung** |
| **unterdrückt_durch_systemregel** | **Konflikt mit Systemregel festgestellt; Systemregel hat Vorrang; Nutzer informiert** |
| **nur_kontextuell_zulässig** | **Regel ist gültig, aber nur in bestimmten Kontexten anwendbar (z. B. nicht bei Koranversen)** |
| **deaktiviert** | **Durch Nutzer temporär deaktiviert; bleibt gespeichert** |
| **vom_nutzer_gesperrt** | **Durch explizite Nutzeraktion oder wiederholte Korrektursignale dauerhaft gesperrt** |

**Zustandsübergänge sind protokolliert und auditierbar.**

**8.3 Konflikttypen und Auflösung**

| **Konflikttyp** | **Auflösung** | **Zielstatus des Stil-Eintrags** |
|----|----|----|
| **Stilregel widerspricht Glossar-Eintrag** | **Glossar gewinnt immer** | **unterdrückt_durch_systemregel** |
| **Stilregel widerspricht Transliterationsregel** | **Transliterationsregel gewinnt; Schreibweise wird angepasst (nicht gelöscht)** | **unterdrückt_durch_systemregel** |
| **Stilregel widerspricht Terminologie-Verzeichnis** | **Terminologie-Verzeichnis gewinnt** | **unterdrückt_durch_systemregel** |
| **Stilregel widerspricht Religiöse Formeln-Verzeichnis** | **Formeln-Verzeichnis gewinnt immer** | **unterdrückt_durch_systemregel** |
| **Stilregel widerspricht Koranvers-Behandlung** | **Externe Quelle gewinnt; Regel im Koranvers-Kontext deaktiviert** | **nur_kontextuell_zulässig** |
| **Stilregel widerspricht Hadith-Verifikationslogik** | **Verifikationslogik gewinnt** | **unterdrückt_durch_systemregel** |
| **Referenzsatz enthält systemregelwidrige Schreibweise** | **Referenzsatz bleibt stilistisch massgeblich; Schreibweise wird angepasst** | **Kein Konflikt am Stil-Eintrag selbst** |
| **Konflikt nicht eindeutig kategorisierbar** | **Nutzer wird zur expliziten Entscheidung aufgefordert** | **Bleibt in in_prüfung bis Entscheidung** |

**8.4 Konflikt-Protokollierung \[KANON\]**

**Jeder Konflikt wird protokolliert mit:**

- **Zeitpunkt.**

- **Konflikttyp.**

- **Betroffener Stil-Eintrag (UUID).**

- **Betroffene Systemregel.**

- **Zustandsübergang.**

- **Nutzer informiert: Ja/Nein.**

- **Nutzerentscheidung (falls erforderlich): ausstehend / getroffen / verworfen.**

9.  **VERSIONIERUNG DES STILPROFILS**

**9.1 Grundsatz \[KANON\] Jede Änderung am Stilprofil erzeugt eine neue Version. Keine Version wird überschrieben.**

**9.2 Stilprofil-Version-Felder**

| **Feld** | **Typ** | **Inhalt** |
|----|----|----|
| **stilprofil_version_uuid** | **UUID** | **Eindeutige ID der Version** |
| **account_uuid** | **UUID** | **Besitzender Account** |
| **version_nummer** | **Integer** | **Monoton steigend** |
| **erstellt_at** | **Timestamp** |  |
| **auslöser** | **Enum** | **neuer_referenzsatz / nutzerakzeptanz / nutzerkorrektur / manuelle_regel / deaktivierung / konfliktauflösung** |
| **delta** | **JSON** | **Geänderte Einträge gegenüber Vorgängerversion** |
| **is_aktiv** | **Boolean** | **Nur eine Version kann aktiv sein** |

**9.3 Unveränderlichkeit angewendeter Versionen \[KANON\] Wenn eine bestimmte Stilprofil-Version auf eine Seite angewendet wurde, ist diese Anwendung unveränderlich. Spätere Stilprofil-Änderungen verändern abgeschlossene Seiten nie automatisch.**

**9.4 Rollback Die Stilprofil-Rollback-Funktion ist \[KANON\] standardmässig aktiv für alle Nutzer mit freigeschaltetem Stilfeature. Der Nutzer kann zu einer früheren stilprofil_version zurückkehren. Rollback betrifft nur künftige Anwendungen, nie abgeschlossene Seiten (siehe §9.3 Unveränderlichkeit angewendeter Versionen). Die UI-Ausgestaltung der Rollback-Bedienung ist \[KONFIG\] produktkonfigurierbar (vgl. Dokument C v1.1 §4.2).**

10. **LERNLOGIK UND VERBESSERUNGSLOGIK**

**10.1 Adaptives Lernsystem \[KANON\] Das System lernt adaptiv. Konfidenzwerte steigen und sinken auf Basis von Nutzeraktionen:**

- **Nutzer bestätigt Vorschlag → Konfidenz steigt.**

- **Nutzer korrigiert Vorschlag → Konfidenz sinkt.**

- **Nutzer ignoriert Vorschlag → kein Signal.**

**Keine automatischen Regelanwendungen ohne ausreichende Konfidenz \[KALIB\].**

**10.2 Was die Lernlogik nie darf \[KANON\]**

- **Glossar-Einträge automatisch überschreiben.**

- **Systemregeln untergraben.**

- **Eine Invariante aus Statistik allein erzeugen.**

- **Einen Kandidaten zur Präferenzregel hochstufen ohne Nutzerbestätigung oder Referenzsatz-Belegdichte.**

**10.3 Neue bestätigte Referenzsätze → Ablauf: siehe Abschnitt 4.4.**

**10.4 Phänomenfeld-Abdeckungsanzeige \[KONFIG\] Das System zeigt dem Nutzer pro Phänomenfeld, wie viele bestätigte Belege vorliegen und welche Felder noch ungenügend abgedeckt sind.**

**10.5 Was nicht gelernt wird \[KANON\]**

- **Vokalisierungsmuster (separat gespeichert).**

- **Koranvers-Wiedergabe (extern: quranenc.com).**

- **Hadith-Texte (Verifikationslogik).**

- **Glossar-Einträge (Systemregel).**

- **Transliterationsregeln (Systemregel).**

11. **QUALITÄTS- UND SICHERHEITSLOGIK**

**11.1 Nur bestätigtes Material \[KANON\] Kein unbestätigtes Material fliesst ins Stilprofil ein.**

**11.2 Keine verdeckte Stilanwendung \[KANON\] Jede Anwendung eines Stilmusters auf einen Übersetzungsvorschlag ist kenntlich gemacht. Kein stilles Anwenden ohne Hinweis.**

**11.3 Transparenz gegenüber dem Nutzer \[KONFIG\] Der Nutzer kann jederzeit einsehen:**

- **Das aktive Stilprofil (gegliedert nach Dimensionen, Phänomenfeldern, Regeltypen).**

- **Konfidenzwert und Status jedes Eintrags.**

- **Belegliste jedes Eintrags (mit Verweis auf AR/DE-Paar).**

- **Phänomenfeld-Abdeckungsstand.**

**11.4 Audit-Pfad \[KANON\] Jede Stilprofil-Anwendung auf einen Übersetzungsvorschlag wird protokolliert:**

- **Welche Stilprofil-Version.**

- **Welche konkreten Stil-Einträge haben den Vorschlag beeinflusst.**

- **Zeitpunkt.**

**11.5 Keine Weitergabe ohne explizite Freigabe \[KANON\] Das Stilprofil eines Accounts wird nie automatisch an andere Accounts weitergegeben.**

**11.6 Stilprofil-Marker (visuelle Kennzeichnung) \[KANON\] Stilbeeinflusste Stellen im Editor werden durch dezente Unterstreichung (Blauton) + Hover-Tooltip mit Regelbezeichnung (PF-XX) kenntlich gemacht. Die Anzeige der Stilmarker ist in den Anzeigeeinstellungen deaktivierbar. Die Anzeigeeinstellung für Stilmarker wird account-level gespeichert.**

12. **GRENZEN DES FEATURES**

**12.1 Inhaltliche Grenzen \[KANON\]**

- **Das Stilprofil kann nur lernen, was in bestätigtem Referenzmaterial vorhanden ist.**

- **Es kann keine Bereiche lernen, für die keine zweisprachigen Belege vorliegen.**

- **Es kann keine Entscheidungen treffen, die einer Systemregel widersprechen.**

**12.2 Kalibrierungsabhängige Grenzen \[KALIB\]**

- **Phänomenfelder mit ungenügender Belegdichte bleiben im Status tendenz oder kandidat.**

- **Konfidenz-Schwellen für automatische Anwendung noch nicht festgelegt.**

**12.3 Anwendungsgrenzen**

- **Abgeschlossene Seiten werden durch spätere Stilprofil-Änderungen nie automatisch verändert \[KANON\].**

- **Das Stilprofil gilt nicht für den OCR-Export-Strang \[KANON\].**

- **Welche Accountklassen das Feature nutzen dürfen, ist produktkonfigurierbar \[KONFIG\].**

13. **WAS AUSDRÜCKLICH NICHT TEIL DES FEATURES IST**

| **Ausgeschlossener Punkt** | **Typ** | **Begründung** |
|----|----|----|
| **Automatisches Überschreiben von Glossar-Einträgen** | **\[KANON\]** | **Systemregel-Vorrang** |
| **Automatisches Überschreiben von Transliterationsregeln** | **\[KANON\]** | **Systemregel-Vorrang** |
| **Automatisches Überschreiben religiöser Formeln** | **\[KANON\]** | **Systemregel-Vorrang** |
| **Anwendung auf Qurʾān-Stellen gemäss §4.15** | **\[KANON\]** | **Externe Quelle, Systemregel** |
| **Anwendung auf Hadith-Texte** | **\[KANON\]** | **Verifikationslogik, Systemregel** |
| **Anwendung auf OCR-Export-Strang** | **\[KANON\]** | **OCR-DOCX ist Quelltext, kein Übersetzungsdokument** |
| **Anwendung auf fremde Accounts** | **\[KANON\]** | **Accountbindung absolut** |
| **Lernen aus unbestätigten Entwürfen** | **\[KANON\]** | **Nur bestätigtes Material** |
| **Lernen aus ignorierten KI-Vorschlägen** | **\[KANON\]** | **Null Signal** |
| **Invariante aus Statistik allein** | **\[KANON\]** | **Invariante nur durch explizite Nutzerhandlung** |
| **Verdeckte Stilanwendung ohne Kenntlichmachung** | **\[KANON\]** | **Transparenzpflicht** |
| **Rückwirkende Änderung abgeschlossener Seiten** | **\[KANON\]** | **Unveränderlichkeit** |
| **Vokalisierungsmuster als Stilmuster** | **\[KANON\]** | **Separat gespeichert** |
| **Stilprofil als Ersatz für Option A** | **\[KANON\]** | **Ergänzung, nicht Ersatz** |

14. **OFFENE PUNKTE (KALIBRIERBAR – NOCH NICHT FESTGELEGT)**

| **Offener Punkt** | **Status** |
|----|----|
| **Mindestanzahl Referenzsätze für Aktivierung** | **\[KALIB\]** |
| **Konfidenz-Schwelle: Kandidat → Tendenz** | **\[KALIB\]** |
| **Konfidenz-Schwelle: Tendenz → Präferenz** | **\[KALIB\]** |
| **Konfidenz-Schwelle für automatische Anwendung (Präferenz)** | **\[KALIB\]** |
| **Mindestbelegdichte pro Phänomenfeld** | **\[KALIB\]** |

**Die Kalibrierungswerte werden nach Gold-Corpus-Tests festgelegt.**

15. **AKTUELLER HANDLUNGSSTATUS**

**Dieses Dokument ist Dokument B v1.2 – Feature-Spezifikation „Erkenne meinen Übersetzungsstil". Es baut auf Dokument A (Kanonischer Nutzerstil-Korpus v1.0) auf und ist als kanonische Stilfeature-Spezifikation eingefroren.**

**Dokument C v1.1 ist die Integrationsnachricht zu diesem Feature und wurde als Integrationsrahmen formal bestätigt. Die in Dokument C v1.1 §3 genannten Folgearbeiten – formale Integrationsanalyse, CRs für Core Architecture Baseline / Engineering Execution Baseline / Delivery Backlog Baseline, Erweiterung bestehender Objekte (account, decision_event, Übersetzungs-Job/Recovery, Provenance/EXPORT_EVENT), Audit-Integration in die A-01–D-03-Struktur, Ticket-Definition, Sprint-Planung, Kalibrierung der offenen Schwellenwerte nach Gold-Corpus-Tests, Coding-Freigabe – bleiben ausdrücklich offen und werden ohne expliziten Nutzerauftrag nicht gezogen.**

**Noch nicht:**

- **Kein Code.**

- **Keine Coding-Freigabe.**

- **Keine Implementierung.**

- **Kein CR ohne expliziten Auftrag.**

- **Keine neue Architektur ausserhalb des bestehenden Kanons.**

**Dokument B v1.2 – Feature-Spezifikation „Erkenne meinen Übersetzungsstil" – kanonisch eingefroren. Nicht als alleinstehende Implementierungsanweisung verwenden.**
