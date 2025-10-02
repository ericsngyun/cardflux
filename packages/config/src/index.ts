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
  mtg: mtgConfig,
  pokemon: pokemonConfig,
  yugioh: yugiohConfig,
  onepiece: onepieceConfig,
  digimon: digimonConfig,
};

export function getGameConfig(slug: string): GameConfig | undefined {
  return games[slug];
}

export function getAllGames(): GameConfig[] {
  return Object.values(games);
}
