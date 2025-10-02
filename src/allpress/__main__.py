from allpress import cli
from allpress.util import logger

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CLI tool for allpress')

    parser.add_argument("-v", "--verbose", action="store_true",)

    subparsers = parser.add_subparsers(dest='command', required=True)

    parser_build_temp = subparsers.add_parser(
        "build_temp",
        help="Build temporary tensor of embeddings to train autoencoders."
    )
    parser_build_temp.add_argument(
        "--max-size",
        type=int,
        help="Max desired size of tensor file. No more embeddings will be created\n " \
        "once this size has been reached."
    )

    parser_train_aes = subparsers.add_parser(
        "train_autoencoders",
        help="Train autoencoders."
    )

    parser_train_aes.add_argument(
        "--epochs",
        type=int,
        help="Number of epochs to train the autoencoders.",
        default=50
    )

    parser_search = subparsers.add_parser(
        "search",
        help="Search VectorDB."
    )
    parser_search.add_argument(
        "-q",
        "--query",
        type=str,
        help="Query string to search."
    )

    parser_search.add_argument(
        "-k1",
        "--top-k1",
        type=int,
        default=10000,
        help="Top k keys to return for first-order search."
    )

    parser_search.add_argument(
        "-k2",
        "--top-k2",
        type=int,
        default=100,
        help="Top k keys to return for second-order search."
    )

    parser_scrape = subparsers.add_parser(
        "scrape",
        help="Scrape."
    )

    parser_scrape.add_argument(
        "-s",
        "--shuffle",
        action="store_true",
        default=True,
        help="Shuffle the dataset before scraping."
    )

    parser_scrape.add_argument(
        "-sv",
        "--save-vectors",
        action="store_true",
        default=True,
        help="Save autoencoded vectors after scraping."
    )

    parser_scrape.add_argument(
        "-i",
        "--iterations",
        type=int,
        default=2,
        help="Number of iterations over a website to make when scraping."
    )

    args = parser.parse_args()

    logger.set_verbose(True)

    if args.command == "build_temp":
        cli.main._build_temp_embed_tensor()

    if args.command == "train_autoencoders":
        cli.main._train_autoencoders(args.epochs)

    if args.command == "scrape":
        shuffle_data = args.shuffle
        save_vectors = args.save_vectors
        iterations = args.iterations
        cli.main._scrape_sources(shuffle_data, save_vectors, iterations)

    if args.command == "search":
        cli.main._search(args.query, args.top_k1, args.top_k2)
