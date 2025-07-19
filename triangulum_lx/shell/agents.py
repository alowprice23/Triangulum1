# This file is part of the Triangulum project.
#
# Triangulum Lx is an autonomous, self-healing software system.
#
# This file contains the implementation of the agent communication system.

import click

def agent_chat():
    """
    Communicate with an agent.
    """
    click.echo("Welcome to the agent chat.")
    click.echo("Type 'exit' to end the chat.")
    while True:
        try:
            message = click.prompt("You >")
            if message == "exit":
                break
            # In a real application, we would send the message to the agent
            # and print the response. For now, we will just echo the message.
            click.echo(f"Agent > {message}")
        except (KeyboardInterrupt, EOFError):
            break
    click.echo("Exiting the agent chat.")
