# Text criteria are marked by a reserved seam and decided by lint

Status: accepted

A criterion about the repository's own authored text, which no change to shipped code alone can make fail, is placed at the seam name `authored-text` that interphase reserves, and its acceptance lines' commands are lint checks the repository's lint stage runs; it carries no test row, adds no locked path, and the record check refuses a test row on it while still refusing every other acceptance line no test implements. We marked it with a reserved seam name, the way the Step name check-author is reserved, because pipeline, mitosis and lighthouse each hold a copy of the record, items, acceptance-line and locked formats and refuse a key or a value they do not know, which ruled out a new criterion key or a new surface family; telling it apart from its command or the file it reads was rejected as a guess. A repository with no lint stage gives such a criterion an ordinary seam and a test row, as before.
