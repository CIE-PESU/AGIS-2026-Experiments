# Backend Instructions

## Database Synchronization
To ensure all developers have the same mentors and admins in their local databases, we use a seed file. 

Whenever you `git pull`, if `backend/scripts/seed_data.json` has been updated, run the following command to sync your local MongoDB instance with the shared data:

```bash
python scripts/sync_db.py
```

**Note:** When you add a new mentor using the Admin Dashboard, the backend will automatically append the new mentor's details to `scripts/seed_data.json`. Be sure to commit this file and push it so your team members can receive the update!

Make sure you have the exact same `FERNET_KEY` in your `.env` file as your team, otherwise you will not be able to log in with the shared encrypted passwords.
