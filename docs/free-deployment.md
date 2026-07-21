# Free Deployment

Updated: 2026-07-21

The current zero-cost production path is a Render Static Site backed by the complete tracked JSON snapshot. It does not create a server, database, disk, or paid instance.

Use [render-free-deployment.md](render-free-deployment.md) for deployment and verification steps.

Optional live-data components remain available:

- GitHub Actions runs the crawler and ETL manually or weekly.
- Supabase Free stores curated rows when a live database is needed.
- The static Render site remains usable if Supabase is paused or not configured.

Legacy AWS, Render Web Service, Neon, Vercel, and GitHub Pages documents are retained only for architecture history; they are not part of the selected deployment.
