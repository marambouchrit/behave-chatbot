"""
generate_admin_hash.py
======================
Script utilitaire à lancer UNE SEULE FOIS pour générer le hash bcrypt
du mot de passe admin, puis copier ce hash dans admin_config.py.

Usage (PowerShell) :
    python generate_admin_hash.py

Ce script n'est PAS importé par l'application. C'est un outil de setup.
Il peut être ajouté au .gitignore si tu ne veux pas le versionner.
"""

from core.security import hash_password


def main() -> None:
    print("=" * 55)
    print("  BeHave Assistant — Génération du hash admin")
    print("=" * 55)

    password = input("\nEntre le mot de passe admin souhaité : ").strip()

    if not password:
        print("\n[ERREUR] Le mot de passe ne peut pas être vide.")
        return

    if len(password) < 8:
        print("\n[AVERTISSEMENT] Mot de passe trop court (minimum 8 caractères recommandés).")

    generated_hash = hash_password(password)

    print("\n[OK] Hash généré avec succès :\n")
    print(f"  {generated_hash}")
    print("\nCopie cette valeur  dans le fichier .env:")
    print('  ADMIN_PASSWORD_HASH: str = "<colle_le_hash_ici>"')
    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()