# Images de test

Ce répertoire contient les images utilisées pour les tests, notamment les images de tickets de caisse pour le test multimodal.

## Format supporté

- JPEG (.jpg, .jpeg)
- PNG (.png)

## Utilisation

Pour utiliser une image dans les tests:

```bash
python test_multimodal_receipt.py download/receipt.jpeg
```

## Ajouter une image

Placez simplement votre image dans ce répertoire et référencez-la dans les tests.

**Note:** Les fichiers d'images sont ignorés par défaut dans `.gitignore` pour éviter d'alourdir le dépôt. 
Si vous souhaitez ajouter une image de démonstration, vous pouvez la commiter explicitement avec `git add -f`.
