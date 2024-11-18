import os
import re
from os.path import expandvars

from cleo.io.io import IO
from dict_deep import deep_get
from poetry.plugins.plugin import Plugin
from poetry.poetry import Poetry
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.repository_pool import Priority
from poetry.toml.file import TOMLFile
from pydantic import validate_call
from pydantic_settings import BaseSettings
from typing_extensions import Self


class PSPConfig(BaseSettings):
    prefix: str = "POETRY_REPOSITORIES_"
    env: bool = True
    toml: bool = True


class PoetrySourcePlugin(Plugin):
    def activate(self, poetry: Poetry, io: IO = None) -> None:
        config: PSPConfig = PSPConfig()

        if config.env:
            repositories = {}
            pattern = re.compile(rf"{config.prefix}(?P<name>[A-Z_]+)_URL")

            for env_key in os.environ.keys():
                match = pattern.match(env_key)
                if match:
                    repositories[match.group("name").lower().replace("_", "-")] = {
                        "env_name": match.group("name"),
                        "url": os.environ[env_key],
                    }

            for name, repository in repositories.items():
                repo = LegacyRepository(name, repository["url"])

                priority_name = os.getenv(
                    f"{config.prefix}{repository['env_name']}_PRIORITY", "primary"
                )

                priorities = {
                    "default": Priority.DEFAULT,
                    "primary": Priority.PRIMARY,
                    "supplemental": Priority.SUPPLEMENTAL,
                    "explicit": Priority.EXPLICIT,
                }

                priority = priorities.get(priority_name.casefold(), Priority.PRIMARY)

                poetry.pool.add_repository(repo, priority=priority)

        if config.toml:
            for repository in poetry.get_sources():
                poetry.pool.remove_repository(repository.name)
                repo = LegacyRepository(
                    expandvars(repository.name), expandvars(repository.url)
                )
                poetry.pool.add_repository(repo, priority=repository.priority)
