import React, {Component, PropTypes} from 'react'


const creator_icon = <div>O</div>
const creator_surround_icon = <div>O</div>
const opponent_icon = <div>X</div>
const opponent_surround_icon = <div>X</div>
const empty_icon = <div></div>

const cell = {
    'padding-left': '8px',
    'background-color': '#b9b9b7',
    'border': '1px solid #333'
};

const coordinates = {
    fontSize: '9px',
    textAlign: 'center'
};

const yellow = {
      'background-color': 'yellow',
};

const black = {
      'background-color': 'black',
};

class GameSquare extends Component {

    constructor(props) {
        super(props)
        this.state = {
            owner: props.owner,
            possession_type: props.possession_type
        }
        this.squareClicked = this.squareClicked.bind(this)
    }

    componentWillReceiveProps(newProps){
        this.setState({
            owner: newProps.owner,
            possession_type: newProps.possession_type
            })
    }

    getStatus(){
        let selected_icon, surrounding_icon = null
        // check to see if this square has an owner`
        if (this.state.owner){
            // there's an ower, so check which owner and then the 
            // "posession type" of the square now:
            // selected = properly owned square
            // surrounding = next to a properly owned square
            if (this.state.owner == this.props.game_creator){      
                // owned by the game creator, so it'll be blue
                selected_icon = creator_icon
                surrounding_icon = creator_surround_icon
            }else{
                selected_icon = opponent_icon
                surrounding_icon = opponent_surround_icon
            }
        }

        switch (this.state.possession_type){
            case "Surrounding":
                return surrounding_icon
            case "Selected":
                return selected_icon
            default:
                return empty_icon       
        }
    }

    checkAvailable(){
        if (this.props.isPlayerTurn()){
            // check if a valid place to make a move
            if (this.state.owner == null){
                // no owner
                
                return true
            }else{
                // owned either as a core spot or a surrounding spot
                return false
            }
        }
       
    }

    takeOwnership(){
        // make the user that clicked, the owner and claim the surrounding spots that are available
        this.props.sendSocketMessage({action: "claim_square", 
                                      square_id: this.props.square_id })
    }

    squareClicked(square){
        // player clicked a square
        if (this.checkAvailable()){
            // available to take ownership
            this.takeOwnership()
        }
        
    }

   
    render() {
        return (
            <td onClick={this.squareClicked} height="30" width="30" style={cell}>
                {this.getStatus()}
            </td>
        )
    }
}

GameSquare.propTypes = {
    loc_x: PropTypes.number,
    loc_y: PropTypes.number,
    square_id: PropTypes.number,
    owner: PropTypes.number,
    possession_type: PropTypes.string,
    game_creator: PropTypes.number,
    sendSocketMessage: PropTypes.func,
    isPlayerTurn: PropTypes.func
}

export default GameSquare

