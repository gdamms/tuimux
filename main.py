from src.tuimux import Tuimux


def main():
    tuimux = Tuimux()

    with tuimux:
        while True:
            key = tuimux.get_key()
            if not tuimux.handle(key):
                break
            tuimux.render()
            tuimux.blink()


if __name__ == '__main__':
    main()
