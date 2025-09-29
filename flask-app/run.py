from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host="10.122.244.64", port=5099, debug=True)
    