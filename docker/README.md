## Getting Started

> [!IMPORTANT]
> This setup is for local demo purposes only and not intended for production use.

1. Copy the `.env.example` file and rename it to `.env`

2. No need to change any variables. If you like, you can set a better password for the `Administrator` user.

3. Start the containers:

    ```bash
    docker compose up -d
    ```

    This will take a while to download the images and start the containers. On the first run, a container named "configurator" will run for a while to set up your site.

4. Access the site at http://test.localhost:8080

5. Log in with username "Administrator" and the password set in `.env` (default: "admin")