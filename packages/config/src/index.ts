import mtgConfig from './mtg.json';
import pokemonConfig from './pokemon.json';
import yugiohConfig from './yugioh.json';
import onepieceConfig from './onepiece.json';
import digimonConfig from './digimon.json';

export interface GameConfig {
  name: string;
  slug: string;
  source: {
    type: 'api' | 'bulk';
    url: string;
    rateLimit?: number;
  };
  schema: {
    id: string;
    name: string;
    set?: string;
    rarity?: string;
    type?: string;
    image?: string;
  };
  normalization: {
    idField: string;
    nameField: string;
    imageField?: string;
  };
}

export const games: Record<string, GameConfig> = {
  mtg: mtgConfig as GameConfig,
  pokemon: pokemonConfig as GameConfig,
  yugioh: yugiohConfig as GameConfig,
  onepiece: onepieceConfig as GameConfig,
  digimon: digimonConfig as GameConfig,
};

export function getGameConfig(slug: string): GameConfig | undefined {
  return games[slug];
}

export function getAllGames(): GameConfig[] {
  return Object.values(games);
}
